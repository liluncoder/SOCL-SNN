import argparse
import math
import os
import sys
import time

import numpy as np

import importlib.util

def _load_mod(fn, name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fn)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

m1 = _load_mod('02_working_memory.py', 'm1pppp')

N_CH = m1.N_CH
N_UNITS = m1.N_UNITS
K_TICKS = m1.K_TICKS
DEC_PERIOD = m1.DEC_PERIOD
ITI = m1.ITI
RESET_DUR = m1.RESET_DUR

ACT_UNIT = 2
N_ACT = 8
N_ACT_TOTAL = N_CH * N_ACT

N_BG2 = m1.N_BG - 1
M2_ARMS = ('memory', 'no_slot', 'freeze_off')

W_ACT = 10.0

def m2_cfg(freeze_w=True):
    import copy
    c = copy.deepcopy(m1.MEM_CFG)
    c['dev'] = {'on': False}
    if freeze_w:
        c['syn'] = {'on': False}
    return c

class ActNet(m1.MemNet):

    def __init__(self, cfg=None, seed=None, arm='memory', n_trial=40,
                 w_act=W_ACT):

        self._m2_arm = arm

        _MAP = {'memory': 'two_pool', 'no_slot': 'snap_off', 'freeze_off': 'two_pool'}
        arm_m1 = _MAP.get(arm, arm)
        super().__init__(cfg=cfg, seed=seed, arm=arm_m1, n_trial=n_trial)

        base = ACT_UNIT * self.nE_slot
        self.ACT = [base + np.arange(c * N_ACT, (c + 1) * N_ACT)
                    for c in range(N_CH)]
        self.ACT_ALL = np.concatenate(self.ACT)
        assert base + N_ACT_TOTAL <= (ACT_UNIT + 1) * self.nE_slot, \
            '工位 2 要放得下 4 群 × %d 动作细胞' % N_ACT
        self.w_act = float(w_act)

        self.hAct = np.zeros(N_CH)

        self._act_log = []

    def _act_current(self, ie):
        if self._m2_arm == 'freeze_off':
            return

        n = np.array([float(self._spk_now(self.POOLB[c]).sum()) for c in range(N_CH)])
        n_rel = n - n.mean()
        for c in range(N_CH):
            if n_rel[c] > 0.0:
                self.hAct[c] = min(1.0, self.hAct[c] + m1.H_UP * self.w_act / 10.0 * n_rel[c])
            else:
                self.hAct[c] *= math.exp(-self.dt / m1.H_DECAY)

    def _act_dynamics(self, ie):

        for c in range(N_CH):
            ie[self.ACT[c]] += m1.W_REC * (m1.LATCH_BASE * self.hAct[c] + self.hAct[c] ** 2)

        w = int(np.argmax(self.hAct))
        if self.hAct[w] > 0.35:
            for c in range(N_CH):
                if c == w:
                    continue
                ie[self.ACT[c]] -= m1.W_LAT * self.hAct[w]
                for k in range(N_CH):
                    if k != c:
                        ie[self.ACT[c]] -= 0.3 * m1.W_LAT * self.hAct[k]

        ie[self.ACT_ALL] -= float(self.cfg['drive']['tonic'])

    def _mem_current(self):
        ie = super()._mem_current()
        self._act_current(ie)
        self._act_dynamics(ie)
        return ie

    def _sample(self):
        if not self._samp:
            return
        s = self._samp[0]
        if s[2] is None:
            s[2] = np.zeros(N_BG2 + 2 * N_CH + N_CH)
            s.append(np.zeros(N_UNITS))
        if self.t > s[0] - m1.SAM_WIN - 1e-9:
            sp = self._spk_now(np.arange(self.N_E))
            u = np.arange(self.N_E) // self.nE_slot
            ok = u >= ACT_UNIT + 1
            np.add.at(s[2][:N_BG2], u[ok] - (ACT_UNIT + 1), sp[ok])
            for c in range(N_CH):
                s[2][N_BG2 + c] += sp[self.POOLA[c]].sum()
                s[2][N_BG2 + N_CH + c] += sp[self.POOLB[c]].sum()
                s[2][N_BG2 + 2 * N_CH + c] += sp[self.ACT[c]].sum()
            np.add.at(s[3], u, sp)
        if self.t >= s[0] - 1e-9:
            self._samp.pop(0)
            self.trials[-1][2].append((s[1], s[2], s[3]))

            self._act_log.append((len(self.trials) - 1, s[1], self.hAct.copy()))

def _run_once(seed, arm, npc, log, w_act=W_ACT, diag=False, freeze_w=True):
    net = ActNet(cfg=m2_cfg(freeze_w), seed=seed, arm=arm, n_trial=npc, w_act=w_act)
    T_END = RESET_DUR + ITI * npc + K_TICKS[-1] * DEC_PERIOD + 200.0
    t0 = time.time()
    while net.t < T_END:
        net.step(1)
    wall = time.time() - t0

    NB = N_BG2
    XA, XB, XACT, y_prev, y_cur = [], [], [], [], []
    prev_ch = None
    for (ts, ch, recs) in net.trials:
        if prev_ch is not None:
            for (k, f, _f25) in recs:
                XA.append(f[:NB + N_CH])
                XB.append(np.concatenate([f[:NB], f[NB + N_CH:NB + 2 * N_CH]]))
                XACT.append(np.concatenate([f[:NB], f[NB + 2 * N_CH:]]))
                y_prev.append(prev_ch)
                y_cur.append(ch)
        prev_ch = ch
    XA, XB, XACT = np.asarray(XA, float), np.asarray(XB, float), np.asarray(XACT, float)
    y_prev, y_cur = np.asarray(y_prev, int), np.asarray(y_cur, int)

    out = {'arm': arm, 'seed': seed, 'w_act': float(w_act), 'wall': wall,
           'n_pair': len(y_prev),
           'rate': float(net.n_spkE.sum() / (net.nE0 * net.nU) / (net.t / 1000.0))}

    def _acc(X, y, shuffle=False):
        n = len(y)
        cut = max(1, int(n * 0.5))
        return m1.decode_nearest_centroid(X[:cut], y[:cut], X[cut:], y[cut:],
                                          shuffle=shuffle, seed=seed)

    acc_act, n_te, cnt_te = _acc(XACT, y_prev)
    acc_act_sh, _, _ = _acc(XACT, y_prev, shuffle=True)
    acc_poolB, _, _ = _acc(XB, y_prev)
    acc_cur, _, _ = _acc(XACT, y_cur)
    out.update(acc_act=acc_act, acc_act_sh=acc_act_sh,
               acc_poolB=acc_poolB, acc_cur=acc_cur,
               n_te=n_te, cnt_te=cnt_te)

    log('  [%s seed=%d w_act=%.1f] %d 配对 ｜ %.0fs ｜ 墙钟 %.0fs ｜ %.1fHz/细胞'
        % (arm, seed, w_act, len(y_prev), T_END / 1000.0, wall, out['rate']))
    log('      ★acc_act（读动作群→解码**上一**通道）** %.3f ** ｜ 打乱 %.3f ｜ 测试 n=%d 每类 %s'
        % (acc_act, acc_act_sh, n_te, cnt_te))
    log('      ·旁证：读池B→上一通道 %.3f（≈M1 的 acc_prev）｜ 读动作群→**当前**通道 %.3f'
        % (acc_poolB, acc_cur))

    tr = net.t / 1000.0
    act_rate = [net.n_spkE[g].sum() / tr / len(g) for g in net.ACT]
    log('      动作群平均放电率：%s'
        % ' '.join('%.2f' % v for v in act_rate))

    SC_K = 3
    hit = tot = 0
    for (ti, k, hv) in net._act_log:
        if k != SC_K or ti == 0:
            continue
        prev = net.trials[ti - 1][1]
        if hv.max() > 0.35:
            tot += 1
            hit += int(int(np.argmax(hv)) == prev)
    act_mean = float(np.mean(act_rate))
    out.update(act_rate=act_mean, act_hit=hit, act_tot=tot)
    log('      ★自检A：动作群平均放电率 **%.2f Hz**（裸细胞基线 ~7.0；应显著更低，要求 <5.0）'
        % act_mean)
    log('      ★自检B：hAct 单热码命中"上一通道" **%d/%d**（要求 ≥80%%）'
        % (hit, max(tot, 1)))
    return out

def run_arm(seed, arm, npc, log, w_act=W_ACT, max_retry=2, diag=False, freeze_w=True):
    for attempt in range(max_retry + 1):
        s = seed + attempt * 10000
        out = _run_once(s, arm, npc, log, w_act=w_act, diag=diag, freeze_w=freeze_w)
        if min(out['cnt_te']) >= 5:
            out['seed'] = s
            return out
        log('      ⚠ 闸门 0 不满足（每类 %s <5）⇒ 重试 seed=%d' % (out['cnt_te'], seed + (attempt + 1) * 10000))
    out['seed'] = s
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=str, default='51')
    ap.add_argument('--arms', type=str, default=','.join(M2_ARMS))
    ap.add_argument('--trials', type=int, default=40)
    ap.add_argument('--w-act', type=float, default=W_ACT, help='槽B→动作群 的冻结通路强度')
    ap.add_argument('--calib-wact', action='store_true',
                    help='★ W_ACT 诊断模式：跑多个 w_act 档，看动作群能否被读出')
    ap.add_argument('--w-act-scan', type=str, default='1,3,10,20,30,50')
    ap.add_argument('--freeze-w', type=int, default=1,
                    help='1=关 STDP（默认，修 `std`→`syn` 键名 bug）；0=复现 2026-10-05 前的旧结果')
    ap.add_argument('--diag', action='store_true')
    ap.add_argument('--log', type=str, default=None)
    ap.add_argument('--smoke', action='store_true', help='只跑 1 个试次，看代码通不通')
    a = ap.parse_args()

    fh = open(a.log, 'w', encoding='utf-8') if a.log else sys.stdout

    def log(*xs):
        s = ' '.join(str(x) for x in xs)
        print(s, flush=True)
        if a.log:
            fh.write(s + '\n')
            fh.flush()

    npc = 2 if a.smoke else a.trials
    log('=' * 78)
    log('03_memory_driven_action ｜ 种子 %s ｜ 臂 %s ｜ 试验 %d ｜ W_ACT=%.1f'
        % (a.seeds, a.arms, npc, a.w_act))
    log('  动作群 = 工位 %d 的 %d 群 × %d 细胞 ｜ 冻结通路 = 槽B(c) → ACT(c)'
        % (ACT_UNIT, N_CH, N_ACT))
    log('  背景工位 = 工位 %d..%d（%d 个）★ 动作工位 %d 已从背景里摘出'
        % (ACT_UNIT + 1, N_UNITS - 1, N_BG2, ACT_UNIT))
    log('=' * 78)

    if a.calib_wact:
        scan = [float(x) for x in a.w_act_scan.split(',') if x]
        sd = int(a.seeds.split(',')[0])
        log('★ W_ACT 诊断：档 = %s ｜ seed=%d ｜ 试验 %d' % (scan, sd, npc))
        log('  %6s  %10s  %10s  %10s  %10s' % ('W_ACT', 'acc_act', '打乱', 'acc_cur', '池B→上一'))
        for w in scan:
            o = _run_once(sd, 'memory', npc, log, w_act=w, freeze_w=bool(a.freeze_w))
            log('  %6.1f  %10.3f  %10.3f  %10.3f  %10.3f'
                % (w, o['acc_act'], o['acc_act_sh'], o['acc_cur'], o['acc_poolB']))
        log('★ 诊断口径：选 acc_act 明显 > 打乱(=0.25) 且 < acc_cur 的那一档；'
            '太弱→不动，太强→饱和。诊断后**写死**到预注册 §二。')
        if a.log:
            fh.close()
        return 0

    rows = []
    for arm in [x for x in a.arms.split(',') if x]:
        for sd in [int(x) for x in a.seeds.split(',') if x]:
            rows.append(run_arm(sd, arm, npc, log, w_act=a.w_act, diag=a.diag,
                                freeze_w=bool(a.freeze_w)))
    log('-' * 78)
    log('汇总（%d 格）' % len(rows))
    log('  %-12s %6s %9s %9s %9s %9s %9s'
        % ('臂', 'seed', 'acc_act', '打乱', 'acc_cur', '池B→上一', 'n_pair'))
    for o in rows:
        log('  %-12s %6d %9.3f %9.3f %9.3f %9.3f %9d'
            % (o['arm'], o['seed'], o['acc_act'], o['acc_act_sh'],
               o['acc_cur'], o['acc_poolB'], o['n_pair']))

    for arm in sorted(set(o['arm'] for o in rows)):
        sub = [o for o in rows if o['arm'] == arm]
        log('  ★ %-12s acc_act 均值 %.3f ｜ 打乱 %.3f ｜ 过零假设 %d/%d'
            % (arm, np.mean([o['acc_act'] for o in sub]),
               np.mean([o['acc_act_sh'] for o in sub]),
               sum(1 for o in sub if o['acc_act'] > 0.30), len(sub)))
    if a.log:
        fh.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())