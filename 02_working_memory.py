import argparse
import importlib.util
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))

def _load(fn, name):
    p = os.path.join(_HERE, fn)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

dev6 = _load('01_substrate.py', 'dev6')

N_UNITS = 25
MEM_UNIT = 0
N_INJ = 8
N_SLOT_A = 6
N_SLOT_B = 6
N_CH = 4
N_BG = N_UNITS - 2
POOL_UNIT_B = 1
INJ_OFF = 0
PA_OFF = N_INJ * N_CH
PB_OFF = 0
assert PA_OFF + N_SLOT_A * N_CH == 56, '工位 0 的预算必须是 56'
assert PB_OFF + N_SLOT_B * N_CH <= 80, '工位 1 要放得下池 B'

STIM_DUR = 30.0
RESET_DUR = 250.0
W_IN = 8.0
W_RESET = -6.0

W_SUB = 30.0
W_WEAK = 0.1
TAU_HOLD = 400.0
W_REC = 5.0
W_LAT = 5.0
H_UP = 0.1
H_DECAY = 2000.0
LATCH_BASE = 0.4
K_TICKS = (2, 3, 5)
DEC_PERIOD = 100.0
ITI = 900.0
SAM_WIN = 60.0
WIN_MS = 20.0
ALPHA = 0.5

ARMS = ('two_pool', 'snap_off', 'sham_B')

MEM_CFG = {
    'n_units': N_UNITS,

    'dev': {'on': False},
    'std': {'on': False},
    'lr': {'topology': 'random'},
    'delay': {'decouple': True},
    'trace': True,
    'bin_ms': 5.0,
}

class MemNet(dev6.Network):

    def __init__(self, cfg=None, seed=None, arm='two_pool', n_trial=40):
        assert arm in ARMS, arm
        self.arm = arm
        super().__init__(cfg or {}, seed=seed)
        self.calib = False

        self.n_trial = int(n_trial)
        rs = np.random.default_rng(int(self.cfg['seed']) * 977 + 13)
        nblk = max(1, self.n_trial // N_CH)
        seq = np.concatenate([rs.permutation(N_CH) for _ in range(nblk)])
        if seq.size < self.n_trial:
            seq = np.concatenate([seq, rs.permutation(N_CH)[:self.n_trial - seq.size]])
        self._seq = seq[:self.n_trial]
        nE = self.nE_slot
        base = MEM_UNIT * nE
        self.INJ = [base + INJ_OFF + np.arange(c * N_INJ, (c + 1) * N_INJ)
                    for c in range(N_CH)]
        self.POOLA = [base + PA_OFF + np.arange(c * N_SLOT_A, (c + 1) * N_SLOT_A)
                      for c in range(N_CH)]
        baseB = POOL_UNIT_B * nE
        self.POOLB = [baseB + PB_OFF + np.arange(c * N_SLOT_B, (c + 1) * N_SLOT_B)
                      for c in range(N_CH)]
        self.INJ_ALL = np.concatenate(self.INJ)
        self.SLOT_A_ALL = np.concatenate(self.POOLA)
        self.SLOT_B_ALL = np.concatenate(self.POOLB)
        self.SLOT = self.POOLA
        self._clear_trial_state()

    def _clear_trial_state(self):
        self.trials = []
        self._i_trial = -1
        self._t_stim = None
        self._stim_left = 0.0
        self._reset_left = 0.0
        self._seq_ptr = 0
        self._samp = []
        self._acc = None
        self.calib_bins = []
        self._calib_buf = None
        self.hA = np.zeros(N_CH)
        self.hB = np.zeros(N_CH)
        self._last_snap = -1
        self._prev_ch = None
        self.hA_log = []
        self._hwin = None
        self.trace_h = False

    def _spk_now(self, cells):
        return (self.t - self.t_lastE[np.asarray(cells)]) <= self.dt + 1e-9

    def _mem_current(self):
        ie = np.zeros(self.N_E)
        t = self.t

        if self._t_stim is None or t >= self._t_stim + ITI - RESET_DUR:

            if self._i_trial >= 0:
                w = int(np.argmax(self.hA)) if float(self.hA.max()) > 0.35 else -1
                self._last_snap = w
                if self.arm == 'two_pool':
                    self.hB[:] = 0.0
                    if w >= 0:
                        self.hB[w] = 1.0

            self._prev_ch = self._ch if self._i_trial >= 0 else None

            self._i_trial += 1
            self._t_stim = t + RESET_DUR
            self._stim_left = STIM_DUR
            self._reset_left = RESET_DUR
            self.hA[:] = 0.0

            self._ch = int(self._seq[self._seq_ptr % len(self._seq)])
            self._seq_ptr += 1
            for k in K_TICKS:
                self._samp.append([self._t_stim + k * DEC_PERIOD, k, None])
            self.trials.append([self._t_stim, self._ch, []])
            if self.calib:
                if self._calib_buf is not None:
                    self.calib_bins.append(self._calib_buf)
                self._calib_buf = np.zeros((50, N_CH))

        if 0.0 < self._reset_left:
            ie[self.SLOT_A_ALL] += W_RESET
            self._reset_left -= self.dt

        if t >= self._t_stim and self._stim_left > 0.0:
            ie[self.INJ[self._ch]] += W_IN
            self._stim_left -= self.dt

        sp = [int(self._spk_now(g).sum()) for g in self.INJ]
        for c in range(N_CH):
            if sp[c]:
                ie[self.POOLA[c]] += W_SUB * sp[c]
                for k in range(N_CH):
                    if k != c:
                        ie[self.POOLA[k]] += W_WEAK * sp[c]

        for h, pool in ((self.hA, self.POOLA), (self.hB, self.POOLB)):

            n = np.array([float(self._spk_now(pool[c]).sum()) for c in range(N_CH)])
            n_rel = n - n.mean()
            for c in range(N_CH):
                if n_rel[c] > 0.0:
                    h[c] = min(1.0, h[c] + H_UP * n_rel[c])
                else:
                    h[c] *= math.exp(-self.dt / H_DECAY)

            for c in range(N_CH):
                ie[pool[c]] += W_REC * (LATCH_BASE * h[c] + h[c] ** 2)

            if W_LAT:
                w = int(np.argmax(h))
                if h[w] > 0.35:
                    for c in range(N_CH):
                        if c == w:
                            continue
                        ie[pool[c]] -= W_LAT * h[w]
                        for k in range(N_CH):
                            if k != c:
                                ie[pool[c]] -= 0.3 * W_LAT * h[k]

        ie[self.SLOT_A_ALL] -= float(self.cfg['drive']['tonic'])
        ie[self.SLOT_B_ALL] -= float(self.cfg['drive']['tonic'])
        if self.calib and self._calib_buf is not None:
            b = int((t - self._t_stim + 300.0) // 100.0)
            if 0 <= b < 50:
                for c in range(N_CH):
                    self._calib_buf[b, c] += int(self._spk_now(self.POOLA[c]).sum())
        return ie

    def step(self, n=1):
        for _ in range(n):
            self.extra_I = self._mem_current()
            super().step(1)
            self._sample()

    def _sample(self):
        if not self._samp:
            return
        s = self._samp[0]
        if s[2] is None:
            s[2] = np.zeros(N_BG + 2 * N_CH)
            s.append(np.zeros(N_UNITS))
        if self.t > s[0] - SAM_WIN - 1e-9:
            sp = self._spk_now(np.arange(self.N_E))
            u = np.arange(self.N_E) // self.nE_slot
            ok = u >= 2
            np.add.at(s[2][:N_BG], u[ok] - 2, sp[ok])
            for c in range(N_CH):
                s[2][N_BG + c] += sp[self.POOLA[c]].sum()
                s[2][N_BG + N_CH + c] += sp[self.POOLB[c]].sum()
            np.add.at(s[3], u, sp)
            if self.trace_h:
                self._hwin = self.hA.copy() if self._hwin is None \
                    else np.maximum(self._hwin, self.hA)
        if self.t >= s[0] - 1e-9:
            self._samp.pop(0)
            self.trials[-1][2].append((s[1], s[2], s[3]))
            if self.trace_h:
                self.hA_log.append((self._i_trial, s[1], self.hA.copy(),
                                    self._hwin.copy() if self._hwin is not None
                                    else np.zeros(N_CH)))
                self._hwin = None

def balanced_acc(X, y, yhat):
    cls = np.unique(y)
    r = []
    for c in cls:
        m = (y == c)
        if m.sum() == 0:
            continue
        r.append(float((yhat[m] == c).mean()))
    return float(np.mean(r)) if r else float('nan')

def decode_nearest_centroid(Xtr, ytr, Xte, yte, shuffle=False, seed=0):
    rng = np.random.default_rng(seed)

    X_all = np.concatenate([Xtr, Xte], axis=0)
    mu = X_all.mean(0)
    sd = np.maximum(X_all.std(0), 0.5)
    Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
    if shuffle:
        ytr = rng.permutation(ytr)
    cls = np.unique(ytr)
    C = np.stack([Ztr[ytr == c].mean(0) for c in cls])
    d = ((Zte[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    yhat = cls[np.argmin(d, 1)]
    cnt = [int((yte == c).sum()) for c in np.unique(yte)]
    return balanced_acc(Xte, yte, yhat), int(len(yte)), cnt

def best_cut(y, yp):
    n = len(y)
    center = n // 2
    lo, hi = int(math.ceil(0.3 * n)), int(math.floor(0.7 * n))
    candidates = []
    for cut in range(lo, hi + 1):
        if cut <= 0 or cut >= n:
            continue
        cy = np.bincount(y[cut:], minlength=N_CH)
        cp = np.bincount(yp[cut:], minlength=N_CH)
        if cy.min() >= 5 and cp.min() >= 5:
            candidates.append(cut)
    if not candidates:
        return center, -1
    return min(candidates, key=lambda c: abs(c - center)), 5

def _run_once(seed, arm, npc, log, bench=False, diag=False, trace=False):
    net = MemNet(cfg=MEM_CFG, seed=seed, arm=arm, n_trial=npc)
    net.trace_h = bool(trace)

    T_END = RESET_DUR + ITI * npc + K_TICKS[-1] * DEC_PERIOD + 200.0
    t0 = time.time()
    while net.t < T_END:
        net.step(1)
    wall = time.time() - t0

    XA, XB, y, y_prev, X_in, ut = [], [], [], [], [], []
    prev_ch = None
    for (ts, ch, recs) in net.trials:

        if prev_ch is not None:
            for (k, f, f25) in recs:
                XA.append(f[:N_BG + N_CH])
                XB.append(np.concatenate([f[:N_BG], f[N_BG + N_CH:]]))
                X_in.append(np.concatenate([f25, f[:N_BG + N_CH]]))
                y.append(ch)
                y_prev.append(prev_ch)
                ut.append(k)
        prev_ch = ch
    XA = np.asarray(XA, float)
    XB = np.asarray(XB, float)
    X_in = np.asarray(X_in, float)
    y = np.asarray(y, int)
    y_prev = np.asarray(y_prev, int)
    ut = np.asarray(ut, int)
    if diag:
        log('    ── 诊断：逐试验「池A 的 4 槽 / 池B 的 4 槽」窗内放电数')
        log('       （期望：池A 只亮"被刺激通道"对应的槽；池B 只亮"上一试次通道"对应的槽）')
        ti = -1
        for (ts, ch, recs) in net.trials:
            ti += 1
            for (k, f, _f25) in recs:
                log('       试验%2d 通道%d k=%d → 池A %s ｜ 池B %s'
                    % (ti, ch, k,
                       ' '.join('%3.0f' % v for v in f[N_BG:N_BG + N_CH]),
                       ' '.join('%3.0f' % v for v in f[N_BG + N_CH:])))
    out = {'arm': arm, 'seed': seed, 'n_trial': len(net.trials), 'wall': wall,
           't_end': T_END / 1000.0, 'rate': float(net.n_spkE.sum() / (net.nE0 * net.nU) /
                                                  (net.t / 1000.0))}
    log('  [%s seed=%d] %d 次试验 ｜ %.0fs 仿真 ｜ 墙钟 %.0fs ｜ 全网 %.1fHz/细胞'
        % (arm, seed, len(net.trials), T_END / 1000.0, wall, out['rate']))
    log('      平均每槽放电率：池A %s ｜ 池B %s'
        % (' '.join('%.1f' % (net.n_spkE[g].sum() / (net.t / 1000.0) / len(g))
                    for g in net.POOLA),
           ' '.join('%.1f' % (net.n_spkE[g].sum() / (net.t / 1000.0) / len(g))
                    for g in net.POOLB)))

    SC_K = 3
    hitA = hitB = pairs = seen = ignite = 0
    prev_ch = None
    for (ts, ch, recs) in net.trials:
        r1 = [r for r in recs if r[0] == SC_K] or [r for r in recs if r[0] == 1]
        if not r1:
            continue
        f = r1[0][1]
        a, b = f[N_BG:N_BG + N_CH], f[N_BG + N_CH:]
        if prev_ch is None:
            ignite += int(b.max() > 0)
        else:
            pairs += 1
            if a.max() > 0:
                hitA += int(int(np.argmax(a)) == ch)
            if b.max() > 0:
                hitB += int(int(np.argmax(b)) == prev_ch)
        seen += 1
        prev_ch = ch
    out.update(hitA=hitA, hitB=hitB, pairs=pairs, ignite=ignite, seen=seen)
    log('      ★机制自检（在 k=%d 上算）：池A 选对槽 **%d/%d** ｜ 池B 选对"上一通道" **%d/%d**'
        ' ｜ 池B 自燃（第 1 试次）%d'
        % (SC_K, hitA, pairs, hitB, pairs, ignite))

    if trace and net.hA_log:

        k_ok = ITI - RESET_DUR
        ch_of = {}
        spk_hit, spk_n, skipped = {}, {}, set()
        for i, (ts_, chv, recs) in enumerate(net.trials):
            ch_of[i] = chv
            for (k, f, _f25) in recs:
                if k * DEC_PERIOD > k_ok:
                    skipped.add(k)
                    continue
                a = f[N_BG:N_BG + N_CH]
                if a.max() > 0:
                    spk_n[k] = spk_n.get(k, 0) + 1
                    spk_hit[k] = spk_hit.get(k, 0) + int(int(np.argmax(a)) == chv)
        h_hit, h_n, h_max, h_end = {}, {}, {}, {}
        for rec in net.hA_log:
            ti, k, h_now, h_win = rec[0], rec[1], rec[2], rec[3]
            if ti not in ch_of or k * DEC_PERIOD > k_ok:
                continue
            if float(h_win.max()) <= 0.05:
                continue
            h_n[k] = h_n.get(k, 0) + 1
            h_hit[k] = h_hit.get(k, 0) + int(int(np.argmax(h_win)) == ch_of[ti])
            h_max[k] = h_max.get(k, 0.0) + float(h_win.max())
            h_end[k] = h_end.get(k, 0.0) + float(h_now.max())
        log('    ★★池A 收敛曲线（"选对槽"命中率随 k；ITI=%.0fms ⇒ 只有 k·100 ≤ %.0f 有效）'
            % (ITI, k_ok))
        if skipped:
            log('       ⚠ 已跳过越界的 k = %s（窗末越过了试次边界）' % sorted(skipped))
        log('       k      h_A 命中(窗内max)    h 窗内max均值   h 采样末均值   放电计数命中')
        for k in sorted(set(list(h_hit) + list(spk_hit))):
            log('       %-5d  %-18s  %-13s  %-13s  %s'
                % (k,
                   ('%d/%d' % (h_hit.get(k, 0), h_n.get(k, 0))) if h_n.get(k) else '—',
                   ('%.3f' % (h_max.get(k, 0.0) / h_n[k])) if h_n.get(k) else '—',
                   ('%.3f' % (h_end.get(k, 0.0) / h_n[k])) if h_n.get(k) else '—',
                   ('%d/%d' % (spk_hit.get(k, 0), spk_n.get(k, 0))) if spk_n.get(k) else '—'))
    for k in K_TICKS:
        m = (ut == k)
        if m.sum() < 8:
            out['k%d' % k] = None
            log('    · k=%d 样本不足（%d）' % (k, int(m.sum())))
            continue
        XAk, XBk, yk, Xik = XA[m], XB[m], y[m], X_in[m]
        yp = y_prev[m]
        n = len(yk)
        cut, cutmin = best_cut(yk, yp)
        tr, te = slice(0, cut), slice(cut, n)

        acc, nte, cnt = decode_nearest_centroid(XAk[tr], yk[tr], XAk[te], yk[te])
        acc_in, _, _ = decode_nearest_centroid(Xik[tr], yk[tr], Xik[te], yk[te])
        nulls = [decode_nearest_centroid(XAk[tr], yk[tr], XAk[te], yk[te],
                                         shuffle=True, seed=1000 + i)[0] for i in range(60)]
        thr = float(np.quantile(nulls, 0.95))

        acc_prev, _, cnt_prev = decode_nearest_centroid(XBk[tr], yp[tr], XBk[te], yp[te])
        nulls_prev = [decode_nearest_centroid(XBk[tr], yp[tr], XBk[te], yp[te],
                                              shuffle=True, seed=2000 + i)[0]
                      for i in range(60)]
        thr_prev = float(np.quantile(nulls_prev, 0.95))
        out['k%d' % k] = {'acc': acc, 'acc_prev': acc_prev,
                          'acc_inj': acc_in, 'null95': thr, 'null95_prev': thr_prev,
                          'n_test': nte, 'cnt': cnt, 'cnt_prev': cnt_prev,
                          'cut': cut, 'cut_min': cutmin, 'n': n}
        log('    · k=%d acc_cur=%.3f（池A）｜ acc_prev=%.3f（池B）（切点 %d ｜ 测试 n=%d）'
            % (k, acc, acc_prev, cut, nte))
        log('        类计数: 本试次 %s ｜ 上一试次 %s'
            % (cnt, cnt_prev))
        log('        零假设上界 cur=%.3f prev=%.3f ｜ 判据 cur %s / prev %s ｜ ★含注入对照 %.3f'
            % (thr, thr_prev,
               '✅' if acc > thr else '❌',
               '✅' if acc_prev > thr_prev else '❌',
               acc_in))
        g0 = (min(cnt) >= 5) and (min(cnt_prev) >= 5)
        log('        ★闸门 0（两个标签集都"每类测试样本 ≥5"）：%s'
            % ('✅ 满足' if g0 else '❌ **不满足** ⇒ 该格记"不可测"（上层会自动 +8 试验重试）'))
        out['k%d' % k]['gate0'] = bool(g0)
    out['gate_all'] = all(
        out.get('k%d' % k) is not None and out['k%d' % k].get('gate0')
        for k in K_TICKS
    )
    return net, out

def run_arm(seed, arm, npc, log, bench=False, diag=False, max_retry=2, trace=False):
    npc = int(npc)
    for att in range(max_retry + 1):
        net, out = _run_once(seed, arm, npc + 8 * att, log, bench=bench, diag=diag, trace=trace)
        out['attempt'] = att
        if out.get('gate_all') or att == max_retry:
            if att:
                log('      ⇒ 关 0 在试验数 %d 时%s' % (npc + 8 * att,
                                                    '满足' if out.get('gate_all') else '仍不满足（作废）'))
            return net, out
        log('      ★关 0 未过 ⇒ 试验数 %d → %d，重试（第 %d 次）'
            % (npc + 8 * att, npc + 8 * (att + 1), att + 1))
    return net, out

def main():
    ap = argparse.ArgumentParser(description='010_v1 工作记忆 · M1（只上 4 个记忆槽）')
    ap.add_argument('--seeds', type=str, default='51')
    ap.add_argument('--arms', type=str, default=','.join(ARMS))
    ap.add_argument('--trials', type=int, default=40, help='每个臂的试验次数')
    ap.add_argument('--smoke', action='store_true', help='只跑 5 秒看机制崩不崩')
    ap.add_argument('--calib', action='store_true',
                    help='★校准：跑几个试验，按 100ms 分箱打印"每槽放电数"')
    ap.add_argument('--w-in', type=float, default=None, help='覆盖刺激幅度')
    ap.add_argument('--w-sub', type=float, default=None, help='覆盖同通道投影')
    ap.add_argument('--w-weak', type=float, default=None, help='覆盖跨通道投影')
    ap.add_argument('--w-rec', type=float, default=None, help='覆盖槽自兴奋')
    ap.add_argument('--w-lat', type=float, default=None, help='覆盖槽间侧抑制（WTA）')
    ap.add_argument('--k-ticks', type=str, default=None,
                    help='逗号分隔的 k 列表，如 1,3,5,10,20,40')
    ap.add_argument('--iti', type=float, default=None, help='试次间隔 ms')
    ap.add_argument('--alpha', type=float, default=None, help='partial_alpha 的衰减系数')
    ap.add_argument('--tau-hold', type=float, default=None,
                    help='覆盖 H_DECAY（保持时间常数 ms）')
    ap.add_argument('--diag', action='store_true', help='逐试验打印 池A/池B 的 4 槽放电数')
    ap.add_argument('--trace-h', action='store_true', help='★诊断：打印 h_A 的收敛曲线（选对槽命中率随 k）')
    ap.add_argument('--max-retry', type=int, default=2,
                    help='关 0 未过时"试验数 +8 重跑"的最大次数（自检时可传 0）')
    ap.add_argument('--bench', action='store_true', help='只跑一个臂量吞吐')
    ap.add_argument('--log', type=str, default=None)
    ap.add_argument('--h-up', type=float, default=None, help='覆盖 H_UP（h 上升步长）')
    args = ap.parse_args()

    global W_IN, W_SUB, W_WEAK, W_REC, TAU_HOLD, W_LAT, H_DECAY, H_UP, K_TICKS, ITI, ALPHA
    if args.w_in is not None:
        W_IN = float(args.w_in)
    if args.w_sub is not None:
        W_SUB = float(args.w_sub)
    if args.w_weak is not None:
        W_WEAK = float(args.w_weak)
    if args.w_rec is not None:
        W_REC = float(args.w_rec)
    if args.w_lat is not None:
        W_LAT = float(args.w_lat)
    if args.tau_hold is not None:
        H_DECAY = float(args.tau_hold)
    if args.k_ticks is not None:
        K_TICKS = tuple(int(x) for x in args.k_ticks.split(','))
    if args.iti is not None:
        ITI = float(args.iti)
    if args.alpha is not None:
        ALPHA = float(args.alpha)
    if args.h_up is not None:
        H_UP = float(args.h_up)

    assert max(K_TICKS) * DEC_PERIOD <= ITI - RESET_DUR + 1e-9, (
        f"K_TICKS 超预算：max={max(K_TICKS)}·{DEC_PERIOD:.0f}ms="
        f"{max(K_TICKS) * DEC_PERIOD:.0f}ms > ITI−RESET_DUR={ITI - RESET_DUR:.0f}ms。"
        f"要么缩小 K_TICKS，要么加大 --iti（每 +1 k 需 +{DEC_PERIOD:.0f}ms）。"
    )
    logf = None
    def log(*a):
        s = ' '.join(str(x) for x in a)
        print(s)
        if logf:
            logf.write(s + '\n')
            logf.flush()

    if args.log:
        logf = open(args.log, 'w', encoding='utf-8', buffering=1)
        log('[日志] 同时写入 %s（UTF-8）' % args.log)
    log('=' * 78)
    log('010_v1 工作记忆 · M1\'\'\'（第 4 篇）—— **两池 + 快照**（判据见 report/010_M1_v1\'\'\'预注册.txt）')
    log('  细胞预算：INJ %d×%d = %d（工位0）｜ 池A %d×%d = %d（工位0）｜ 池B %d×%d = %d（**工位%d**）'
        % (N_CH, N_INJ, N_CH * N_INJ, N_CH, N_SLOT_A, N_CH * N_SLOT_A,
           N_CH, N_SLOT_B, N_CH * N_SLOT_B, POOL_UNIT_B))
    log('  参数：W_IN %.1f ｜ W_SUB %.2f ｜ W_WEAK %.2f ｜ W_REC %.2f ｜ W_LAT %.2f ｜ '
        'H_UP %.2f ｜ LATCH_BASE %.2f ｜ H_DECAY %.0fms ｜ ITI %.0fms ｜ '
        'K_TICKS %s ｜ SAM_WIN %.0fms ｜ 最大重试 %d'
        % (W_IN, W_SUB, W_WEAK, W_REC, W_LAT, H_UP, LATCH_BASE, H_DECAY, ITI,
           K_TICKS, SAM_WIN, int(args.max_retry)))
    log('=' * 78)

    if args.smoke:
        net = MemNet(cfg=MEM_CFG, seed=int(args.seeds), arm='two_pool')
        t0 = time.time()
        while net.t < 5000.0:
            net.step(1)
        log('  smoke 通过：%.0fs 仿真用 %.0fs 墙钟（≈%.1f s 墙钟/仿真秒）'
            % (net.t / 1000.0, time.time() - t0, (time.time() - t0) / (net.t / 1000.0)))
        log('  试验数 %d ｜ 全网 %.1f Hz/细胞 ｜ 各槽放电率 %s'
            % (len(net.trials), net.n_spkE.sum() / (net.nE0 * net.nU) / (net.t / 1000.0),
               ' '.join('%.1f' % (net.n_spkE[g].sum() / (net.t / 1000.0) / len(g))
                        for g in net.SLOT)))
        log('  注入细胞放电率 %s'
            % ' '.join('%.1f' % (net.n_spkE[g].sum() / (net.t / 1000.0) / len(g))
                       for g in net.INJ))
        return 0

    if args.calib:
        net = MemNet(cfg=MEM_CFG, seed=int(str(args.seeds).split(',')[0]), arm='two_pool')
        net.calib = True
        T = RESET_DUR + ITI * int(args.trials) + 600.0
        t0 = time.time()
        while net.t < T:
            net.step(1)
        if net._calib_buf is not None:
            net.calib_bins.append(net._calib_buf)
        log('  ── 校准：每次试验「每槽放电数」按 100ms 分箱（bin3 覆盖刺激时刻 0~30ms）')
        log('     %.0fs 仿真 ｜ 墙钟 %.0fs' % (net.t / 1000.0, time.time() - t0))
        for i, B in enumerate(net.calib_bins):
            ch = net.trials[i][1] if i < len(net.trials) else -1
            log('     试验%d 通道%d' % (i, ch))
            for b in range(50):
                log('        bin%2d [%+4d,%+4d)ms  %s'
                    % (b, -300 + 100 * b, -200 + 100 * b,
                       ' '.join('%4d' % v for v in B[b])))
        return 0

    seeds = [int(x) for x in str(args.seeds).split(',')]
    arms = [a.strip() for a in str(args.arms).split(',') if a.strip()]
    npc = 6 if args.bench else int(args.trials)
    for arm in arms:
        for sd in seeds:
            run_arm(sd, arm, npc, log, bench=args.bench, diag=args.diag,
                    max_retry=int(args.max_retry), trace=args.trace_h)
    if logf:
        logf.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
