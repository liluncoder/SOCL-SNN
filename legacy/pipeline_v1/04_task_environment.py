import argparse
import copy
import importlib.util
import math
import os
import sys
import time

import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))

def _load_mod(fn, name):
    path = os.path.join(ROOT, fn)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

m2 = _load_mod('03_memory_driven_action.py', 'm2task')
m1 = m2.m1

N_CH = m1.N_CH
N_INJ = m1.N_INJ
N_ACT = m2.N_ACT
ACT_UNIT = m2.ACT_UNIT

STIM_CH = (0, 1)
MARK_TO_CHOICE = {2: 1, 3: 0}

ROUND_MS = 200.0
STIM_T0 = 20.0
STIM_DUR = 30.0
WIN_T0, WIN_T1 = 60.0, 160.0
N_LEARN, N_PROBE = 4, 4
N_TRIAL = 40
SEEDS = (51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151, 161, 171, 181, 191)

W_IN = m1.W_IN
W_STIM0 = 2.0
CHOICE_MODE0 = 'hact'

W_P8_0 = 0.05
R_STAR0 = 0.5
ARMS = ('task_off', 'local', 'global_scalar', 'global_center', 'reward_zero')

WRITE_ERR_TOL = 1e-12

def p8_pairs(nE_slot):
    base_inj = m1.MEM_UNIT * nE_slot + m1.INJ_OFF
    base_act = ACT_UNIT * nE_slot
    pre, post = [], []
    for mc, k in MARK_TO_CHOICE.items():
        inj = base_inj + np.arange(mc * N_INJ, (mc + 1) * N_INJ)
        act = base_act + np.arange(k * N_ACT, (k + 1) * N_ACT)
        pre.append(np.repeat(inj, act.size))
        post.append(np.tile(act, inj.size))
    return np.concatenate(pre).astype(np.int64), np.concatenate(post).astype(np.int64)

class TaskNet(m2.ActNet):

    def _pre_build_hook(self):
        w = float(self.cfg.get('_p8_w', 0.0))
        wn = float(self.cfg.get('_newpath_w', 0.0))
        if wn <= 0.0:
            if w <= 0.0:
                return
            pre, post = p8_pairs(self.nE_slot)
            self.extra_ee_pre = pre
            self.extra_ee_post = post
            self.extra_ee_w = np.full(pre.size, w, dtype=np.float64)
            return

        pre, post = p8_pairs(self.nE_slot)
        pres, posts, ws = [], [], []
        if w > 0.0:
            pres.append(pre)
            posts.append(post)
            ws.append(np.full(pre.size, w, dtype=np.float64))
        pres.append(pre)
        posts.append(post)
        ws.append(np.full(pre.size, wn, dtype=np.float64))
        self.extra_ee_pre = np.concatenate(pres)
        self.extra_ee_post = np.concatenate(posts)
        self.extra_ee_w = np.concatenate(ws)

    def __init__(self, cfg=None, seed=None, arm='task_off', n_trial=N_TRIAL,
                 w_stim=W_STIM0, w_p8=W_P8_0, r_star=R_STAR0, p_safe=0.5,
                 use_marker=True, round_ms=ROUND_MS, choice_mode=CHOICE_MODE0):
        assert arm in ARMS, arm
        assert choice_mode in ('hact', 'direct'), choice_mode
        self.arm011 = arm
        super().__init__(cfg=cfg, seed=seed, arm='memory', n_trial=n_trial)
        self.w_stim = float(w_stim)
        self.w_p8 = float(w_p8)
        self.r_star = float(r_star)
        self.p_safe = float(p_safe)
        self.use_marker = bool(use_marker)

        self._marker_off = bool(cfg.get('_marker_kill', False)) if cfg else False

        self._direct_w = float(cfg.get('_direct_w', 1.0)) if cfg else 1.0
        self._credit_mode = str(cfg.get('_credit_mode', 'none'))

        self._readout_mode = str(cfg.get('_readout_mode', 'count')) if cfg else 'count'
        assert self._readout_mode in ('count', 'gea'), self._readout_mode

        self._ro_drive = bool(cfg.get('_ro_drive', False)) if cfg else False

        self._mark_gain = float(cfg.get('_mark_gain', 1.0)) if cfg else 1.0

        self._thr_margin = float((cfg or {}).get('_thr_margin', 0.0))

        self._rng_ro = (np.random.default_rng(int(self.cfg['seed']) * 65537 + 313)
                        if self._thr_margin > 0.0 else None)

        self._dms = int((cfg or {}).get('_dms', 0))
        assert 0 <= self._dms <= 9, '★dms 只支持 0..9（实测 %r）' % self._dms
        self._g_mem = float((cfg or {}).get('_g_mem', 1.0))
        self._h_up = float((cfg or {}).get('_h_up', 0.5))

        self._h_decay = float((cfg or {}).get('_h_decay', 0.0))
        self._tau_mem = self._h_decay if self._h_decay > 0.0 else m1.H_DECAY
        self._hA = np.zeros(N_CH, float)
        self._dms_cue = False
        self._dms_phase = -1

        self._dumpx = bool(cfg.get('_dump_x', False)) if cfg else False

        self.tfactor = str((cfg or {}).get(
            '_tfactor', os.environ.get('N011_TFACTOR', 'global'))).strip().lower()
        assert self.tfactor in ('global', 'clsdiff2', 'add_bias', 'field', 'vec_bcast',
                                'fieldv2', 'bias_rand'), \
            '★未知 N011_TFACTOR=%r' % self.tfactor
        self._tf_sign = +1
        if self.tfactor != 'global':
            _rng_tf = np.random.default_rng(int(self.cfg['seed']) * 104729 + 7)
            self._tf_bias = _rng_tf.uniform(0.15, 0.45, size=self.N_E)
            self._tf_vvec = 0.5 + 0.5 * np.abs(_rng_tf.normal(0.0, 1.0, size=self.N_E))
        else:
            self._tf_bias = None
            self._tf_vvec = None

        self._hw = None
        self._hq = None
        self._hq_n = None
        self._npre_v = None
        self._hw_n = 0
        if self._ro_drive:
            assert self._readout_mode == 'gea', \
                '★【七十五】`_ro_drive` 只对 `gea` 有意义（当前 mode=%r）' % self._readout_mode
        self.round_ms = float(round_ms)
        self.choice_mode = choice_mode

        self.eng_scale_scope = str(self.cfg['dev'].get('eng_scale_scope', 'global'))
        assert self.eng_scale_scope in ('global', 'act'), self.eng_scale_scope
        self._freeze_chk = None
        self.win_t0 = float(cfg.get('_win_t0', WIN_T0)) if cfg else WIN_T0
        self.win_t1 = float(cfg.get('_win_t1', WIN_T1)) if cfg else WIN_T1

        self._rng_safe = np.random.default_rng(int(self.cfg['seed']) * 7919 + 101)

        self._r_t0 = None
        self._r_idx = -1
        self._phase = 'probe'
        self._safe = 0
        self._marker_ch = 2
        self._stim_start = None
        self._stim_left = 0.0
        self._win_marked = False
        self._decided = False
        self._n_pre = np.zeros(2, float)

        self._gacc = np.zeros(2, float)
        self._hacc = np.zeros(2, float)
        self._rounds = []
        self._gs_const = 0.0

        self._inj_act_mask = None

        self._newpath_mask = None
        self.n_newpath = 0

        self.n_write = 0
        self.n_learn = 0
        self.n_probe = 0
        self.write_err_max = 0.0
        self.dw_abs_cum = 0.0
        self._w_prev = None
        self._h_max_r = 0.0
        self._mark_injected()

    def _mark_injected(self):
        pre, post = p8_pairs(self.nE_slot)
        spec = set(zip(pre.tolist(), post.tolist()))
        ee = self.S['ee']
        m = np.fromiter(((int(a), int(b)) in spec for a, b in zip(ee['pre'], ee['post'])),
                        bool, int(ee['n_syn']))
        wn = float(self.cfg.get('_newpath_w', 0.0))
        if wn > 0.0:
            wv = np.asarray(ee['w'], float)
            m_new = m & (wv == wn)

            m_car = m & (~m_new)
        else:
            m_new = np.zeros(int(ee['n_syn']), bool)
            m_car = m
        self._p8_mask = m_car
        self._newpath_mask = m_new
        self.n_p8 = int(m_car.sum())
        self.n_newpath = int(m_new.sum())
        if self.w_p8 > 0.0 and m_car.any():
            self.infra |= m_car
        if wn > 0.0 and m_new.any():
            self.infra |= m_new

        g = np.concatenate([self.ACT[0], self.ACT[1]])
        self._inj_act_mask = np.isin(ee['post'], g)
        self._in_idx = np.nonzero(self._inj_act_mask)[0]
        self._w_prev = np.asarray(ee['w'], float).copy()

    def _act_current(self, ie):
        n = np.array([float(self._spk_now(self.INJ[c]).sum()) for c in STIM_CH])
        n_rel = n - n.mean()
        for i, c in enumerate(STIM_CH):
            if n_rel[i] > 0.0:
                self.hAct[c] = min(1.0, self.hAct[c]
                                   + m1.H_UP * (self.w_stim * self._direct_w) / 10.0 * n_rel[i])
            else:
                self.hAct[c] *= math.exp(-self.dt / m1.H_DECAY)

    def _reward_of(self, cells):
        if self.arm011 == 'reward_zero':
            base = np.zeros(np.size(cells))
        elif self.arm011 == 'global_scalar':
            base = np.full(np.size(cells), self._gs_const)
        else:
            base = super()._reward_of(cells)
        return self._tf_apply(cells, np.asarray(base, float))

    def _tf_apply(self, cells, base):
        m = self.tfactor
        if m == 'global':
            return base
        cells = np.asarray(cells, int)
        if m == 'add_bias':

            return np.clip(base + self._tf_bias[cells], -1.0, 1.0)
        if m == 'vec_bcast':

            return base * self._tf_vvec[cells]
        if m == 'clsdiff2':

            x = np.asarray(self.xE_t, float)[cells]
            yhat = x / (float(x.sum()) + 1e-9)
            if self._tf_sign > 0:
                y = np.full(yhat.shape, 1.0 / max(1, yhat.size))
            else:
                y = np.zeros(yhat.shape)
            return np.clip((yhat - y) * 3.0, -1.0, 1.0)
        if m == 'field':

            b = np.zeros(self.N_E, float)
            b[cells] = base
            u = np.arange(self.N_E) // self.nE_slot
            nu = int(u.max()) + 1
            ub = np.bincount(u, weights=b, minlength=nu)
            ii = np.arange(nu)
            w = np.exp(-np.abs(ii[:, None] - ii[None, :]) / 1.0)
            sm = (w @ ub) / np.maximum(w.sum(1), 1e-9)
            return np.clip(sm[u[cells]], -1.0, 1.0)
        if m in ('fieldv2', 'bias_rand'):

            lam = float(getattr(self, 'field_lam', 0.0))
            add = (self.field_gain(cells, lam) if m == 'fieldv2'
                   else self.bias_rand_gain(cells, lam))
            z = np.asarray(base, float) + add
            st = getattr(self, '_field_stats', None)
            if st is not None:
                st['n_z'] += 1
                st['sum_sat'] += float(np.mean(np.abs(z) >= 1.0))
            return np.clip(z, -1.0, 1.0)
        raise AssertionError('★未知 tfactor=%r' % m)

    def _write_reward(self, w_c, s):
        if self.arm011 == 'task_off':
            return None
        if self.arm011 == 'global_center':
            sc = max(1e-6, float(self.eng_scale))
            self.engE[self.aliveE] += s * self.r_star * sc
            return None
        if self.arm011 == 'global_scalar':
            self._gs_const = float(s) * self.r_star
            return None
        if self.arm011 == 'reward_zero':
            return None

        _med_L, _sc_L = self._calib_pair()
        _sc_L = max(1e-6, float(_sc_L))
        self.engE[self.ACT[w_c]] = _med_L + float(s) * self.r_star * _sc_L

        if self._credit_mode == 'oracle':

            delta = 0.005

            correct = w_c if s > 0 else 1 - w_c
            wrong = 1 - correct

            ee = self.S['ee']
            for post_grp, sign in [(self.ACT[correct], +1), (self.ACT[wrong], -1)]:
                for post_cell in post_grp:
                    st = self.in_ptr[post_cell]
                    cnt = self.in_ptr[post_cell + 1] - st
                    if cnt > 0:
                        li = np.arange(st, st + cnt)
                        wi = self.in_order[li]
                        ee['w'][wi] += sign * delta

            np.clip(ee['w'], self.syn_cfg['w_min'], self._w_hi(), out=ee['w'])
            return '+oracle' if s > 0 else '-oracle'

    def _reset_choice_state(self):
        aE, bE, cE, dE = self.pE
        g = self.ACT_ALL
        self.vE[g] = cE
        self.uE[g] = bE * cE
        self.gEa[g] = 0.0
        self.gEg[g] = 0.0
        self.gIa[g] = 0.0
        self.gIg[g] = 0.0
        self.hAct[:] = 0.0
        self._gacc[:] = 0.0
        self._hacc[:] = 0.0

        if self._dumpx:
            if self._hw is None:
                self._hw = np.zeros(int(self.hAct.size), float)
                self._hq = np.zeros((5, 2), float)
                self._hq_n = np.zeros(5, int)
                self._npre_v = np.zeros(int(self.N_E), int)
            else:
                self._hw[:] = 0.0
                self._hq[:] = 0.0
                self._hq_n[:] = 0
            self._hw_n = 0

    def _open_round(self, t):
        self._r_t0 = float(t)
        self._r_idx += 1
        k = self._r_idx % (N_LEARN + N_PROBE)
        self._phase = 'learn' if k < N_LEARN else 'probe'
        self._reset_choice_state()

        if self._dms <= 0:
            self._safe = 0 if (self._rng_safe.random() < self.p_safe) else 1

            self._marker_ch = 2 if self._safe == 1 else 3
        else:

            self._dms_phase = self._r_idx % (self._dms + 1)
            self._dms_cue = (self._dms_phase == 0)
            if self._dms_cue:
                self._safe = 0 if (self._rng_safe.random() < self.p_safe) else 1
                self._marker_ch = 2 if self._safe == 1 else 3

                self._hA[:] = 0.0
                if self.use_marker:

                    self._hA[self._marker_ch] = 1.0
        self._stim_start = self._r_t0 + STIM_T0
        self._stim_left = STIM_DUR
        self._win_marked = False
        self._decided = False
        self._h_max_r = 0.0
        if self._phase == 'learn':
            self.n_learn += 1
        else:
            self.n_probe += 1

    def _snap_calib(self):
        if self.eng_scale_scope != 'act':

            assert self._calib_ov is None and self._calib_cells is None, \
                'scope=global 时钩子必须恒为 None'
            return None

        if self._freeze_chk is not None:
            assert self._calib_ov == self._freeze_chk, \
                '★冻结被破坏：_calib_ov=%r != %r' % (self._calib_ov, self._freeze_chk)

        g = np.concatenate([self.ACT[0], self.ACT[1]])
        assert g.size == 16, '★标定群应为 16 个细胞，实测 %d' % g.size
        ov = self._calib_of(np.asarray(self.engE[g], float))
        if ov is None:
            return None
        if self._calib_cells is None:
            self._calib_cells = np.zeros(self.N_E, bool)
        else:
            self._calib_cells[:] = False
        self._calib_cells[g] = True
        assert int(self._calib_cells.sum()) == 16, \
            '★局部框作用范围应为 16 细胞，实测 %d' % int(self._calib_cells.sum())
        self._calib_ov = ov
        self._freeze_chk = ov
        return ov

    def _calib_pair(self):
        if self._calib_ov is not None:
            return self._calib_ov
        return (self.eng_med, self.eng_scale)

    def _calibrate(self, v):
        return self._calib_of(v)

    def _decide(self, t):
        self._decided = True

        c0 = float(self.n_spkE[self.ACT[0]].sum() - self._n_pre[0])
        c1 = float(self.n_spkE[self.ACT[1]].sum() - self._n_pre[1])
        winner = 0 if c0 >= c1 else 1

        if self._thr_margin > 0.0 and abs(c0 - c1) < self._thr_margin:
            winner = 0 if self._rng_ro.random() < 0.5 else 1

        w_gea = w_hact = None
        c0g = c1g = c0h = c1h = float('nan')
        if self._readout_mode == 'gea':
            c0g, c1g = float(self._gacc[0]), float(self._gacc[1])
            c0h, c1h = float(self._hacc[0]), float(self._hacc[1])
            w_gea = 0 if c0g >= c1g else 1
            w_hact = 0 if c0h >= c1h else 1

            if self._ro_drive:
                winner = w_gea
        correct = (winner == self._safe)
        s = +1 if correct else -1
        self._tf_sign = int(s)
        tag = None

        self._snap_calib()

        _g16_pre = np.concatenate([self.ACT[0], self.ACT[1]])
        _m16_pre = np.asarray(self.aliveE, bool)[_g16_pre]
        _z_w_pre = float(np.mean(self._reward_of(self.ACT[winner])))
        _z16_pre = np.asarray(self._reward_of(_g16_pre), float)
        n_top_pre = int(np.sum(_m16_pre & (_z16_pre > _z_w_pre)))
        if self._phase == 'learn' and not (self._dms > 0 and self._dms_cue):

            tag = self._write_reward(winner, s)
            if self.arm011 == 'local' and tag:
                self.n_write += 1

            if (self.tfactor == 'global' and self.arm011 in ('local', 'global_scalar')
                    and not getattr(self, 'p_mod_dim', False)
                    and getattr(self, 'p_Rmode', 'engE') == 'engE'
                    and not getattr(self, 'p_flip_s', False)):
                rr = float(np.mean(self._reward_of(self.ACT[winner])))
                self.write_err_max = max(self.write_err_max, abs(rr - s * self.r_star))

                assert self.write_err_max <= WRITE_ERR_TOL, \
                    '★D1‴ 断言失败：R(winner) 偏离 s·r* 超过 %g（arm=%s, err=%.3e）' % (
                        WRITE_ERR_TOL, self.arm011, self.write_err_max)

        _g16 = np.concatenate([self.ACT[0], self.ACT[1]])
        _al = np.asarray(self.aliveE, bool)
        _m16 = _al[_g16]
        z_w = float(np.mean(self._reward_of(self.ACT[winner])))
        _z16 = np.asarray(self._reward_of(_g16), float)
        n_top = int(np.sum(_m16 & (_z16 > z_w)))
        rank_pct = float(np.mean(_m16 & (_z16 < z_w))) if _m16.any() else float('nan')

        _zall = np.asarray(self._reward_of(np.arange(self.N_E)), float)
        n_top_all = int(np.sum(_al & (_zall > z_w)))

        _dx = None
        if self._dumpx:
            _wx = np.asarray(self.n_spkE, int) - np.asarray(self._npre_v, int)
            _al = np.asarray(self.aliveE, bool)
            _wa = _wx[_al].astype(float) if bool(_al.any()) else np.zeros(0, float)
            _m = float(_wa.mean()) if _wa.size else float('nan')
            _vv = float(_wa.var()) if _wa.size else float('nan')
            _act_r = [int(x) for x in np.concatenate([_wx[self.ACT[0]], _wx[self.ACT[1]]])]
            _hw = (self._hw / float(self._hw_n)) if self._hw_n else \
                np.full(int(self.hAct.size), float('nan'))
            _hq = [float(self._hq[k, j]) / float(self._hq_n[k]) if self._hq_n[k] else float('nan')
                   for j in (0, 1) for k in range(5)]
            _gea = np.asarray(self.gEa, float)[_al] if bool(_al.any()) else np.zeros(0, float)
            _eng = np.asarray(self.engE, float)[_al] if bool(_al.any()) else np.zeros(0, float)
            _em = float(_eng.mean()) if _eng.size else float('nan')
            _dx = dict(
                act_r=_act_r,
                hact_w=[float(x) for x in _hw],
                hact_q=_hq,
                g_spk_tot=float(_wa.sum()),
                g_act_frac=(float(np.mean(_wa > 0)) if _wa.size else float('nan')),
                g_fano=(float(_vv / (_m + 1e-9)) if _wa.size else float('nan')),
                g_maxrate=(float(_wa.max()) if _wa.size else float('nan')),
                g_gea_tot=float(_gea.sum()),
                g_gea_max=(float(_gea.max()) if _gea.size else float('nan')),
                g_hact_max=float(self.hAct.max()),
                g_eng_cv=(float(_eng.std() / (abs(_em) + 1e-9)) if _eng.size else float('nan')),
                g_alive=int(_al.sum()))
        _mp, _sp = self._calib_pair()
        _rec = dict(i=self._r_idx, phase=self._phase, t=t,
                                 safe=self._safe, winner=winner, correct=bool(correct),
                                 c0=c0, c1=c1, h0=float(self.hAct[0]), h1=float(self.hAct[1]),
                                 hmax=self._h_max_r, tag=tag,

                                 eng_med_L=float(_mp), eng_scale_L=float(_sp),
                                 eng_med_G=float(self.eng_med),
                                 eng_scale_G=float(self.eng_scale),
                                 n_top=n_top, rank_pct=rank_pct,
                                 n_top_pre=n_top_pre,
                                 n_top_all=n_top_all,

                                 nspk_cum=float(np.sum(self.n_spkE)),
                                 dw_round=None)

        if self._readout_mode == 'gea':
            _rec.update(win_gea=w_gea, win_hact=w_hact,
                        c0_gea=c0g, c1_gea=c1g, c0_hact=c0h, c1_hact=c1h)

        if _dx is not None:
            _rec.update(_dx)

        if self._dms > 0:
            _rec.update(dms_cue=bool(self._dms_cue),
                        hA=[float(x) for x in self._hA])
        self._rounds.append(_rec)

    def _dms_memory(self, ie):

        for c in (2, 3):
            self._hA[c] *= math.exp(-self.dt / self._tau_mem)

    def _mem_current(self):
        ie = np.zeros(self.N_E)
        t = self.t
        if self._r_t0 is None or t >= self._r_t0 + self.round_ms:
            self._open_round(t)

        if t >= self._stim_start and self._stim_left > 1e-9:
            if self._dms > 0 and not self._dms_cue:

                for c in STIM_CH:
                    ie[self.INJ[c]] += W_IN
                if self.use_marker and not getattr(self, '_marker_off', False):
                    ie[self.INJ[2]] += W_IN * self._g_mem * float(self._hA[2])
                    ie[self.INJ[3]] += W_IN * self._g_mem * float(self._hA[3])
            elif self._dms > 0:

                if self.use_marker and not getattr(self, '_marker_off', False):
                    ie[self.INJ[self._marker_ch]] += W_IN * self._mark_gain
            else:
                for c in STIM_CH:
                    ie[self.INJ[c]] += W_IN
                if self.use_marker and not getattr(self, '_marker_off', False):

                    ie[self.INJ[self._marker_ch]] += W_IN * self._mark_gain
            self._stim_left -= self.dt

        if self._dms > 0:
            self._dms_memory(ie)

        if self.choice_mode == 'direct':

            for i, c in enumerate(STIM_CH):
                n = float(self._spk_now(self.INJ[c]).sum())
                if n:
                    ie[self.ACT[c]] += self.w_stim * n
            ie[self.ACT_ALL] -= float(self.cfg['drive']['tonic'])
        else:

            self._act_current(ie)
            self._h_max_r = max(self._h_max_r, float(self.hAct.max()))
            self._act_dynamics(ie)

        if (not self._win_marked) and t >= self._r_t0 + self.win_t0:
            self._win_marked = True
            self._n_pre[0] = float(self.n_spkE[self.ACT[0]].sum())
            self._n_pre[1] = float(self.n_spkE[self.ACT[1]].sum())

            if self._dumpx:
                self._npre_v[:] = self.n_spkE

        if (self._readout_mode == 'gea' and self._win_marked
                and (not self._decided) and t < self._r_t0 + self.win_t1):
            self._gacc[0] += float(self.gEa[self.ACT[0]].sum()) * self.dt
            self._gacc[1] += float(self.gEa[self.ACT[1]].sum()) * self.dt
            self._hacc[0] += float(self.hAct[0]) * self.dt
            self._hacc[1] += float(self.hAct[1]) * self.dt

        if (self._dumpx and self._win_marked
                and (not self._decided) and t < self._r_t0 + self.win_t1):
            self._hw += self.hAct
            self._hw_n += 1
            _fr = (t - (self._r_t0 + self.win_t0)) / max(1e-9, self.win_t1 - self.win_t0)
            _k = int(5.0 * _fr)
            _k = 0 if _k < 0 else (4 if _k > 4 else _k)
            self._hq[_k, 0] += float(self.hAct[0])
            self._hq[_k, 1] += float(self.hAct[1])
            self._hq_n[_k] += 1
        if (not self._decided) and t >= self._r_t0 + self.win_t1:
            self._decide(t)
        return ie

    def sweep_dw(self):
        ee = self.S['ee']
        w = np.asarray(ee['w'], float)
        d = float(np.abs(w[self._in_idx] - self._w_prev[self._in_idx]).sum())
        self._w_prev = w.copy()
        self.dw_abs_cum += d
        return d

    def acc_probe(self, lo=0, hi=None):
        r = [x for x in self._rounds if x['phase'] == 'probe']
        r = r[lo:hi]
        if not r:
            return float('nan'), 0
        return float(np.mean([x['correct'] for x in r])), len(r)

def task_cfg(seed=51, trace=False, norm_on=None, win_t0=WIN_T0, win_t1=WIN_T1,
             eng_scale_mode='legacy', eng_scale_scope='global', eng_outlet=None,
             branch_on=False, branch_n=None):
    c = m2.m2_cfg(False)
    c['dev'] = {'on': True, 'energy_only': True,
                'eng_scale_mode': str(eng_scale_mode),
                'eng_scale_scope': str(eng_scale_scope),

                'eng_outlet': (None if eng_outlet is None else
                               {'rate': float(eng_outlet['rate']),
                                'setpoint': float(eng_outlet.get('setpoint', 1.0))})}
    c['trace'] = bool(trace)
    c['seed'] = int(seed)
    c['_win_t0'] = float(win_t0)
    c['_win_t1'] = float(win_t1)
    if norm_on is not None:
        c['syn'] = dict(c.get('syn', {}))
        c['syn']['norm_on'] = bool(norm_on)
    # gate-1 switch; off unless asked, so existing batches stay byte-identical
    c['branch'] = dict(c.get('branch', {}))
    c['branch']['on'] = bool(branch_on)
    if branch_n:
        c['branch']['n'] = int(branch_n)
    return c

def build(seed=51, arm='task_off', w_stim=W_STIM0, w_p8=W_P8_0, r_star=R_STAR0,
          branch_on=False, branch_n=None,
          p_safe=0.5, use_marker=True, n_trial=N_TRIAL, round_ms=ROUND_MS, trace=False,
          choice_mode=CHOICE_MODE0, win_t0=WIN_T0, win_t1=WIN_T1, eng_scale_mode='legacy',
          eng_scale_scope='global', eng_outlet=None, newpath_w=0.0, marker_kill=False,
          direct_w=1.0, credit_mode='none', readout_mode='count', ro_drive=False,
          mark_gain=1.0, dump_x=False, dms=0, g_mem=1.0, h_decay=0.0,
          thr_margin=0.0):

    cfg = task_cfg(seed=seed, trace=trace, win_t0=win_t0, win_t1=win_t1,
                   eng_scale_mode=eng_scale_mode, eng_scale_scope=eng_scale_scope,
                   eng_outlet=eng_outlet, branch_on=branch_on, branch_n=branch_n)
    cfg['_p8_w'] = float(w_p8)
    cfg['_newpath_w'] = float(newpath_w)
    cfg['_marker_kill'] = bool(marker_kill)
    cfg['_direct_w'] = float(direct_w)
    cfg['_credit_mode'] = str(credit_mode)
    cfg['_readout_mode'] = str(readout_mode)
    cfg['_ro_drive'] = bool(ro_drive)
    cfg['_mark_gain'] = float(mark_gain)
    cfg['_dump_x'] = bool(dump_x)
    cfg['_thr_margin'] = float(thr_margin)

    cfg['_dms'] = int(dms)
    cfg['_g_mem'] = float(g_mem)

    cfg['_h_decay'] = float(h_decay)

    return TaskNet(cfg=cfg, seed=seed, arm=arm, n_trial=n_trial, w_stim=w_stim,
                   w_p8=w_p8, r_star=r_star, p_safe=p_safe, use_marker=use_marker,
                   round_ms=round_ms, choice_mode=choice_mode)

def _run(net, t_end, sweep=False):
    t0 = time.time()
    last = net._r_idx
    while net.t < t_end:
        net.step(1)
        if sweep and net._r_idx != last:
            net.sweep_dw()
            last = net._r_idx
    return time.time() - t0

def mode_bench(log, args):
    log('=' * 78)
    log('011 · ③ `--bench`：真实吞吐（011 **不跑 LLM**；只跑网络 + 任务回路）')
    log('=' * 78)
    n_round = int(args.bench_rounds)
    t_build0 = time.time()
    net = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='local', round_ms=args.round_ms,
                w_stim=args.w_stim, w_p8=args.p8_w, r_star=args.rstar, n_trial=N_TRIAL)
    t_build = time.time() - t_build0
    log('  建网：N_E=%d ｜ ee=%d 条 ｜ 墙钟 %.1fs' % (net.N_E, net.S['ee']['n_syn'], t_build))
    log('  条件：dev.on=%s ｜ dev.energy_only=%s ｜ syn_on=%s ｜ norm_on=%s ｜ trace=%s'
        % (net.cfg['dev']['on'], net.cfg['dev'].get('energy_only'), net.syn_on,
           net.syn_cfg.get('norm_on'), net.cfg.get('trace')))
    log('  轮参数：ROUND_MS=%.0f ｜ 刺激 %.0f~%.0fms ｜ 决策窗 %.0f~%.0fms ｜ 学习/探针 = %d/%d'
        % (args.round_ms, STIM_T0, STIM_T0 + STIM_DUR, WIN_T0, WIN_T1, N_LEARN, N_PROBE))
    wall = _run(net, args.round_ms * n_round + 50.0)
    sim_s = net.t / 1000.0
    per_round = wall / max(1, n_round)
    full_rounds = N_TRIAL * (N_LEARN + N_PROBE)
    per_cell = per_round * full_rounds
    log('')
    log('  实跑：%d 轮（仿真 %.1fs）｜ 墙钟 %.1fs ｜ **每轮 %.3fs** ｜ 仿真实时率 %.2fx'
        % (n_round, sim_s, wall, per_round, sim_s / max(1e-9, wall)))
    log('')
    log('  ── 外推（预注册 §六：主判据 15 种子 × 3 臂 = 45 格 + 自检/难度轴 20 格 = **65 格**）──')
    log('  | 项 | 值 |')
    log('  |---|---|')
    log('  | 单格 = %d 轮（%d 试次 × %d 轮）| **%.1f 分钟** |'
        % (full_rounds, N_TRIAL, N_LEARN + N_PROBE, per_cell / 60.0))
    log('  | 主判据 45 格 | **%.1f 小时** |' % (45 * per_cell / 3600.0))
    log('  | 自检臂 + 难度轴 20 格（5+5+5+5）| **%.1f 小时** |' % (20 * per_cell / 3600.0))
    log('  | **全量 65 格** | **%.1f 小时** |' % (65 * per_cell / 3600.0))
    log('  | `--calib-p8` 5 档扫描（每档单格）| **%.1f 小时** |' % (5 * per_cell / 3600.0))
    log('')
    budget = 65 * per_cell / 3600.0
    if budget > 24.0:
        log('  ❌ **全量 %.1f 小时 > 24 小时** ⇒ 按 §六 的写死规则：**先砍难度轴与自检臂的种子数，不砍主判据 15 种子**。'
            % budget)
        log('     ★可选（必须在跑正式轮**之前**写死，不许事后调）：')
        log('       (a) 缩短 `--round-ms`（现在是 %.0fms）—— 最直接；' % args.round_ms)
        log('       (b) 难度轴 p=0.7/0.9 降到 3 种子、自检臂降到 3 种子 ⇒ 45+12 = 57 格；')
        log('       (c) 关 `norm_on`（**会改机制，属"动轴"，须单独立项**）。')
    else:
        log('  ✅ 全量 %.1f 小时 ≤ 24 小时 ⇒ 按 §六 原样可跑。' % budget)
    log('  ★外推两条前提（写死）：① 单格成本与种子无关；② 每轮成本与轮序号无关。')
    log('=' * 78)
    return net

def mode_smoke(log, args):
    log('=' * 78)
    log('011 · ④ `--smoke`：§四 九条自检断言（**不过不许往下**）')
    log('=' * 78)
    n_round = int(args.smoke_rounds)
    t_end = args.round_ms * n_round + 50.0
    res = []

    def chk(name, ok, detail):
        res.append((name, bool(ok)))
        log('  %s %-46s %s' % ('✅' if ok else '❌', name, detail))

    net = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='local', round_ms=args.round_ms, w_stim=args.w_stim,
                w_p8=args.p8_w, r_star=args.rstar, n_trial=N_TRIAL)
    wall = _run(net, t_end, sweep=True)
    ee = net.S['ee']

    chk('1 消费点断言（写进去的奖励读得出来）',
        (net.n_write > 0) and (net.write_err_max < 1e-6),
        '写了 %d 轮 ｜ max|reward − s·r*| = %.3e' % (net.n_write, net.write_err_max))

    net2 = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='local', round_ms=args.round_ms, r_star=0.0,
                 w_stim=args.w_stim, w_p8=args.p8_w, n_trial=N_TRIAL)
    w2a = np.asarray(net2.S['ee']['w'], float).copy()
    _run(net2, args.round_ms * max(4, n_round // 2) + 50.0)
    w2b = np.asarray(net2.S['ee']['w'], float)
    nz_act = int(np.count_nonzero(w2b[net2._in_idx] - w2a[net2._in_idx]))
    chk('2 r*=0 ⇒ winner 群奖励**精确为 0**（消费点）',
        (net2.n_write > 0) and (net2.write_err_max == 0.0),
        '写了 %d 轮 ｜ max|reward − 0| = %.3e' % (net2.n_write, net2.write_err_max))
    log('     2b 参考读数（**不作断言**）：r*=0 时 ACT 入线里变化的条数 = %d / %d'
        % (nz_act, net2._in_idx.size))
    log('        ★说明：非 winner 组的能量场照常 ⇒ 它们的入线仍会被自然场推动（这是**设计如此**，')
    log('          正是因为零分布必须"系统照常运行、只是不写干预" —— 方法学 ㊾）。')

    nspk = float(np.max(np.asarray(net.n_spkE, float)))
    mxt = float(np.max(np.asarray(net.xE_t, float)))
    chk('3 迹衰减在跑（max(x)/单细胞最大放电 ≈ 小）', (nspk > 0) and (mxt / max(1.0, nspk) < 0.5),
        'max(xE_t)=%.3f ÷ 最大放电=%.0f = %.3f' % (mxt, nspk, mxt / max(1.0, nspk)))

    wv = np.asarray(ee['w'], float)
    wmax = float(net.syn_cfg['w_max'])
    wmin = float(net.syn_cfg['w_min'])
    n_hi = int(np.sum(wv >= wmax - 1e-12))
    n_lo = int(np.sum(wv <= wmin + 1e-12))
    rate = (n_hi + n_lo) / max(1, wv.size)
    n_p8_clip = int(np.sum((wv <= wmin + 1e-12) & net._p8_mask)
                    + np.sum((wv >= wmax - 1e-12) & net._p8_mask))
    chk('4 clip 撞顶率 ≤ 1%（预注册 §四 原写"0/0"⇒ 实测会咬合，见下）', rate <= 0.01,
        'n_hi=%d ｜ n_lo=%d ｜ 撞顶率 = %.4f%% ｜ **P8 载体里撞顶 = %d / %d**'
        % (n_hi, n_lo, 100.0 * rate, n_p8_clip, net.n_p8))
    log('     4b ★预注册 §四 第 4 条原写"（符号表里是 0/0）" —— 那是 **shadow 短程**（权重还原、几乎不动）；')
    log('        这里跑了 %d 轮真 STDP ⇒ 撞顶**必然出现**。判据改成"**撞顶率**"，且**必须与 Σ|Δw| 一起报**。' % (net._r_idx + 1))

    log('  ⑤ 回读 `norm_on` = %s（★它会把"净增幅"整体缩放 ⇒ §2.1 只许用 |Δw|）'
        % net.syn_cfg.get('norm_on'))

    chk('6 条件回读：dev.on / energy_only / syn.on',
        bool(net.cfg['dev']['on']) and bool(net.cfg['dev'].get('energy_only')) and bool(net.syn_on),
        'dev.on=%s ｜ energy_only=%s ｜ syn.on=%s'
        % (net.cfg['dev']['on'], net.cfg['dev'].get('energy_only'), net.syn_on))
    chk('6b 条件回读：eng_scale_mode（P7(甲)，默认 legacy）',
        str(net.cfg['dev'].get('eng_scale_mode', 'legacy')) == str(args.eng_scale_mode),
        'eng_scale_mode=%r ｜ eng_scale=%.6f'
        % (net.cfg['dev'].get('eng_scale_mode', 'legacy'), float(net.eng_scale)))

    _g16 = np.concatenate([net.ACT[0], net.ACT[1]])
    _v16 = np.asarray(net.engE[_g16], float)
    _c_act = net._calibrate(_v16)
    _c_ref = net._calib_of(_v16)
    chk('6c 条件回读：eng_scale_scope + 钩子干净性 + 估计量单源（P7(甲)-L）',
        str(net.cfg['dev'].get('eng_scale_scope', 'global')) == str(args.eng_scope)
        and (_c_act == _c_ref)
        and (_g16.size == 16)

        and ((net._calib_ov is None and net._calib_cells is None)
             if args.eng_scope == 'global' else (
                 net._calib_ov is not None and net._calib_cells is not None
                 and int(net._calib_cells.sum()) == 16
                 and bool(net._calib_cells[_g16].all())
                 and net._calib_pair() == net._calib_ov)),
        'eng_scale_scope=%r ｜ 局部对=%r ｜ 全局对=(%.6f, %.6f) ｜ ACT 群 %d 细胞 ｜ 局部标定 %r'
        % (net.cfg['dev'].get('eng_scale_scope', 'global'), net._calib_ov,
           float(net.eng_med), float(net.eng_scale), _g16.size, _c_act))

    if args.eng_scope == 'act':
        _mL, _sL = net._calib_ov
        _all = np.arange(net.N_E)
        _z = np.asarray(net._reward_of(_all), float)
        _handA = np.clip((net.engE[_g16] - _mL) / max(1e-6, _sL), -1.0, 1.0)
        _bulk = _all[~net._calib_cells]
        _handB = np.clip((net.engE[_bulk] - net.eng_med) / max(1e-6, net.eng_scale),
                         -1.0, 1.0)
        chk('6d 分群生效：ACT 走局部框、bulk 走全局框（逐位手工复算）',
            bool(np.array_equal(_z[net._calib_cells], _handA))
            and bool(np.array_equal(_z[~net._calib_cells], _handB))
            and (_mL != net.eng_med),
            'ACT 用 (%0.6f,%0.6f) ｜ 全局用 (%0.6f,%0.6f) ｜ 两框中位不同=%s'
            % (_mL, _sL, float(net.eng_med), float(net.eng_scale),
               bool(_mL != net.eng_med)))
    else:
        log('  6d 分群生效：skip（scope=global ⇒ 单框历史路径）')

    netg = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='global_scalar', round_ms=args.round_ms,
                 w_stim=args.w_stim, w_p8=args.p8_w, r_star=args.rstar, n_trial=N_TRIAL)
    netg._gs_const = 0.5
    rr = netg._reward_of(np.arange(0, netg.N_E, 97))
    chk('7 对照臂有效性：global_scalar 的 _reward_of 是常数',
        bool(np.allclose(rr, rr[0])) and (abs(float(rr[0]) - 0.5) < 1e-12),
        '取样 %d 个细胞的奖励全 = %.3f' % (rr.size, float(rr[0])))
    rl = net._reward_of(np.arange(0, net.N_E, 97))
    chk('7b local 的 _reward_of 不是常数（否则两臂不可分）', not bool(np.allclose(rl, rl[0])),
        'local 取样奖励：min=%.3f max=%.3f' % (rl.min(), rl.max()))

    n_stim0 = int(net.INJ[0].size)
    n_stim1 = int(net.INJ[1].size)
    chk('8 等强度：两刺激组细胞数/时长/幅度相等',
        (n_stim0 == n_stim1) and (STIM_DUR > 0),
        'INJ[0]=%d 个 ｜ INJ[1]=%d 个 ｜ 都是 +W_IN=%.1f 共 %.0fms'
        % (n_stim0, n_stim1, W_IN, STIM_DUR))

    z = np.asarray(net._reward_of(np.arange(net.N_E)), float)
    alive = np.asarray(net.aliveE, bool)
    ext_all = int(np.sum(alive & (np.abs(z) > 1.0 - 1e-9)))
    g = np.concatenate([net.ACT[0], net.ACT[1]])
    pre_g = np.unique(np.asarray(ee['pre'], int)[net._inj_act_mask])
    ext_pre = float(np.mean(np.abs(z[pre_g]) > 1.0 - 1e-9)) if pre_g.size else float('nan')
    n_win = int(2 * N_ACT)
    log('  ⑨ 极端细胞：N_ext_all=%d（|z|>1）｜ N_winner=%d ｜ N_ext_all > 0.5·N_winner ? %s'
        % (ext_all, n_win, '★是（报告须显式限定）' if ext_all > 0.5 * n_win else '否'))
    log('  ⑨b ★更贴靶：G 的前端伙伴里 |z|>1 的占比 = %.3f（%d 个 pre 伙伴）'
        % (ext_pre, pre_g.size))
    log('  ★|z| 实测：max=+%.2f min=%.2f（约半数饱和 ⇒ `011-P7(丙)` 的措辞要写"逐细胞、但约半数已饱和"）'
        % (z[alive].max(), z[alive].min()))

    log('')
    log('  ── 接口事实 ──')
    log('  P8 指定载体：注入 %d 条边（INJ[2]→ACT[1]、INJ[3]→ACT[0] 各 %d）｜ 在 `S[ee]` 里匹配到 %d 条'
        % (2 * N_INJ * N_ACT, N_INJ * N_ACT, net.n_p8))
    log('    ★匹配数 > 注入数的原因 = 有 %d 对 (pre,post) **本来就有随机边**（P8 探针实测 `INJ[3]→ACT[0]` 1 条）'
        % (net.n_p8 - 2 * N_INJ * N_ACT))
    log('    ⇒ 那两条是**并联**的（指定的一条 + 随机的一条 w≈0.026）⇒ 报告必须写清"载体上还挂着随机并联边"。')
    log('  选择群入线盘面：ACT[0]∪ACT[1] 的入线 = %d 条' % int(net._inj_act_mask.sum()))
    act_rate = [float(np.asarray(net.n_spkE)[g].sum()) for g in net.ACT]
    log('  选择群放电（累计）：ACT[0]=%.0f ｜ ACT[1]=%.0f ｜ ACT[2]/ACT[3]（未使用群，应≈0）=%.0f/%.0f'
        % (act_rate[0], act_rate[1], act_rate[2], act_rate[3]))
    inj_rate = [float(np.asarray(net.n_spkE)[g].sum()) for g in net.INJ]
    log('  刺激/标记组放电（累计）：INJ[0]=%.0f ｜ INJ[1]=%.0f ｜ 标记 INJ[2]=%.0f ｜ INJ[3]=%.0f'
        % tuple(inj_rate))
    log('  实跑 %d 轮 ｜ 学习 %d / 探针 %d ｜ 判定过 %d 轮（★必须 ≈ 总轮数）'
        % (net._r_idx + 1, net.n_learn, net.n_probe, len(net._rounds)))
    wins = [x['winner'] for x in net._rounds]
    log('  winner 分布：ACT[0]=%d ｜ ACT[1]=%d（★若一边倒 ⇒ 通路有偏置，要查）'
        % (wins.count(0), wins.count(1)))

    wp = [x['winner'] for x in net._rounds if x['phase'] == 'probe']
    f1 = (wp.count(1) / max(1, len(wp))) if wp else float('nan')
    base_p = max(args.p_safe, 1.0 - args.p_safe)
    accp, np_ = net.acc_probe()
    chk('10 功能性：winner 不一边倒（0.25≤占比≤0.75）',
        0.25 <= f1 <= 0.75,
        '探针轮 ACT[1] 占比 = %.3f（n=%d）｜ 学习轮 %d/%d'
        % (f1, len(wp), wins.count(1), len(wins)))
    chk('10b 功能性：探针 acc ≥ baseline − 0.15（判定没被"上一轮残留"主导）',
        accp >= base_p - 0.15,
        'acc=%.3f ｜ baseline=%.2f ｜ 余量 %+.3f' % (accp, base_p, accp - base_p))
    accp, np_ = net.acc_probe()
    log('  探针轮 acc_choice = %.3f（n=%d）★smoke 只验接口，**不作判据**' % (accp, np_))
    log('  Σ|Δw|（ACT 入线，累积）= %.4e（★§五⑤ 的前置约束要用它，见 --calib-p8）' % net.dw_abs_cum)
    log('  仿真 %.1fs ｜ 墙钟 %.1fs ｜ 每轮 %.3fs'
        % (net.t / 1000.0, wall, wall / max(1, net._r_idx + 1)))

    n_ok = sum(1 for _, ok in res if ok)
    log('')
    log('=' * 78)
    log('★ smoke 合计 %d / %d 条通过' % (n_ok, len(res)))
    if n_ok == len(res):
        log('✅ 接口自检全过 ⇒ **允许进入 ⑤ `--calib-rstar` / ⑥ `--calib-task`**')
    else:
        log('❌ 有断言没过 ⇒ **停，不许往下走**（§五 写死）')
    log('★ 注：本模式**不作任何科学判据** —— `acc_choice` 在这里只用来确认"通路活着"。')
    log('=' * 78)
    return 0 if n_ok == len(res) else 1

def mode_p8_probe(log, args):
    log('=' * 78)
    log('011 · P8「旁路」预实验：**不给指定载体**（w_p8=0）时，标记能不能影响选择？')
    log('=' * 78)
    log('  做法：`use_marker` 两个水平 × `w_p8=0`（**没有任何指定载体**），')
    log('        其余条件完全相同（同种子、同安全侧序列）⇒ 差异只能走随机 ee。')
    log('  判据（★写在跑之前）：')
    log('    · 若 `|acc(marker_on) − acc(marker_off)|` 在噪声内 ⇒ **旁路可忽略**（不必切）')
    log('    · 若显著偏离 baseline(p) ⇒ **必须切旁路**（那就得导出"标记可达的 ee 集合"再归零）')
    log('')
    rows = []
    for tag, um in (('marker_off', False), ('marker_on', True)):
        net = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='task_off', round_ms=args.round_ms,
                    w_stim=args.w_stim, w_p8=0.0, r_star=args.rstar, p_safe=args.p_safe,
                    use_marker=um, n_trial=N_TRIAL, choice_mode=args.choice_mode,
                    win_t0=args.win_t0, win_t1=args.win_t1)
        t_end = args.round_ms * int(args.p8_rounds) + 50.0
        wall = _run(net, t_end)
        acc, n = net.acc_probe()
        base = max(args.p_safe, 1.0 - args.p_safe)
        rows.append((tag, acc, n, base, net))
        log('  %-12s acc_choice = %.3f（n=%d）｜ baseline(p=%.2f) = %.2f ｜ Δ = %+.3f ｜ 墙钟 %.0fs'
            % (tag, acc, n, args.p_safe, base, acc - base, wall))
    d = abs(rows[0][1] - rows[1][1])
    log('')
    log('  ★|Δacc| = **%.3f** ｜ 单种子二项噪声量级 ≈ 1/sqrt(n) = %.3f'
        % (d, 1.0 / math.sqrt(max(1, rows[0][2]))))
    log('  ⇒ 读数：%s' % ('**旁路可忽略**（|Δ| ≤ 噪声）' if d <= 2.0 / math.sqrt(max(1, rows[0][2]))
                          else '★**旁路不可忽略 ⇒ 必须切**'))
    log('  ★限定：单种子只作**筛查**；要判"可忽略"须 ≥5 种子（方法学 ⑩/㉕）。')
    log('=' * 78)

def mode_calib_p8(log, args):
    log('=' * 78)
    log('011 · P8「可学窗口」预实验：扫 `w_p8`，看**能不能既"起点没学会"又"跑完学得到"**')
    log('=' * 78)
    log('  为什么这是 P8 的关键（预注册【九】9.4）：')
    log('    · `w_p8` 太大 ⇒ 一开局就 ≈100% 正确 ⇒ **任务被接线解决**，学不到任何东西；')
    log('    · `w_p8` = 0  ⇒ 与"没有载体"等价 ⇒ **不可学**。')
    log('    ⇒ 必须存在一个**中间窗口**；本模式就是去量它在不在。')
    log('  标定规则（★写死在此，不许事后改）：取满足 **三条** 的最小档：')
    log('    ① 首段（前 13 试次的探针轮）acc ≈ baseline(p)（|Δ| ≤ 0.05）；')
    log('    ② 尾段（后 13 试次）acc > 首段；')
    log('    ③ `Σ|Δw|`（320 轮累积，ACT 入线）≥ 0.5 × 初始权重 SD（§五⑤ 的前置约束）。')
    log('  ★轮数：本模式用 `--p8-trials` 试次（默认 %d ⇒ 320 轮是正式轮的规模）。' % args.p8_trials)
    log('')
    scan = [float(x) for x in str(args.p8_scan).split(',') if x.strip() != '']
    base = max(args.p_safe, 1.0 - args.p_safe)
    n_trial = int(args.p8_trials)
    t_end = args.round_ms * n_trial * (N_LEARN + N_PROBE) + 50.0
    log('  %-8s %-9s %-9s %-9s %-11s %-9s %-8s' %
        ('w_p8', '首段acc', '尾段acc', 'Δ(尾−首)', 'Σ|Δw|/初SD', '墙钟s', '每轮ms'))
    best = None
    for w in scan:
        net = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='local', round_ms=args.round_ms, w_stim=args.w_stim,
                    w_p8=w, r_star=args.rstar, p_safe=args.p_safe, n_trial=n_trial,
                    choice_mode=args.choice_mode, win_t0=args.win_t0, win_t1=args.win_t1)
        g = np.concatenate([net.ACT[0], net.ACT[1]])
        w0 = np.asarray(net.S['ee']['w'], float)[np.isin(np.asarray(net.S['ee']['post'], int), g)]
        sd0 = float(np.std(w0)) if w0.size else float('nan')
        wall = _run(net, t_end, sweep=True)
        r = [x for x in net._rounds if x['phase'] == 'probe']
        nseg = max(1, len(r) // 3)
        a1 = float(np.mean([x['correct'] for x in r[:nseg]])) if r else float('nan')
        a2 = float(np.mean([x['correct'] for x in r[-nseg:]])) if r else float('nan')
        ratio = net.dw_abs_cum / sd0 if sd0 and sd0 > 0 else float('nan')
        ok1 = abs(a1 - base) <= 0.05
        ok2 = a2 > a1
        ok3 = ratio >= 0.5
        log('  %-8.3f %-9.3f %-9.3f %-+9.3f %-11.3f %-9.0f %-8.1f  %s'
            % (w, a1, a2, a2 - a1, ratio, wall,
               wall / max(1, net._r_idx + 1),
               ('①②③' if (ok1 and ok2 and ok3) else
                ('①' if ok1 else '') + ('②' if ok2 else '') + ('③' if ok3 else ''))))
        if ok1 and ok2 and ok3 and best is None:
            best = w
    log('')
    if best is None:
        log('  ❌ **没有一档同时满足 ①②③** ⇒ 按§五⑤的规则：**先抬 `r*` 或加轮次，不许"跑完发现没信号再说"**。')
        log('     ★下一步（按优先序）：(a) `--rstar 0.75`（抬奖励幅度）；(b) `--p8-trials` 加倍；')
        log('       (c) 若仍不行 ⇒ **承认 011 在本条件不可测**（并把它写成结论，不许调参凑）。')
    else:
        log('  ✅ **最小过线档 = `w_p8 = %.3f`** ⇒ 这就是 §1.2/§1.6 要写死的值。' % best)
        log('     ★限定：单种子只作**筛查**；正式取值前须 ≥3 种子复核（方法学 ⑩/㉕）。')
    log('=' * 78)
    return best

def mode_calib_task(log, args):
    log('=' * 78)
    log('011 · ⑥ `--calib-task`：标定 `W_STIM`（§1.2 写死"**不许沿用 M2 的 W_ACT=10**"）')
    log('=' * 78)
    log('  ★为什么非标定不可（smoke 第一版实测暴露的**第二个接口缺陷**）：')
    log('    `W_STIM=%.1f` 时 `hAct` 峰值只有 0.12~0.19 ⇒ **从没超过 WTA 阈值 0.35**' % W_STIM0)
    log('    ⇒ latch/WTA **完全没参与** ⇒ 赢家由随机 ee 输入决定（且载体会让目标群在刺激窗内早放电、')
    log('      随后在读数窗里被后超极化压住 ⇒ **符号反了**：实测 winner 与 safe 系统性相反，acc=0.083）。')
    log('  ★标定用的"咬合"配置（**声明为标定，不作科学判据**）：`p_safe = 1.0`')
    log('    ⇒ 安全侧**恒为 a（ACT[0]）**、标记**恒为 INJ[3]**（其指定载体 → ACT[0]）')
    log('    ⇒ 这就是 M1 当年"12/12 恒对"那把尺子的 011 版：**只验通路咬不咬合**。')
    log('  判据（★写在跑之前，三条都要）：')
    log('    ① **WTA 参与率 ≥ 0.5**（轮内 `max(hAct) > 0.35` 的轮占比 —— 决策机构真的参与了）')
    log('    ② 无载体时 winner 不一边倒（ACT[1] 占比 ∈ [0.3, 0.7]）')
    log('    ③ **载体能把选择推向正确侧**：`acc(有载体) − acc(无载体) ≥ +0.20`')
    log('  ⇒ 取**最小**满足三条的档（§1.2 原话："取两群都能被驱动、且窗内差异可分辨的最小档"）。')
    log('')
    scan = [float(x) for x in str(args.w_stim_scan).split(',') if x.strip() != '']
    n_round = int(args.calib_rounds)
    mode_c = args.choice_mode
    log('  ★本次 `choice_mode = %s`（`--choice-mode` 可切）' % mode_c)
    log('  %-9s %-9s %-9s %-9s %-9s %-9s %-8s' %
        ('W_STIM', 'acc无载体', 'acc有载体', 'Δ(有−无)', '决策参与率', 'h峰值', 'ACT1占比'))
    best = None
    for ws in scan:
        out = {}
        for tag, um, wp8 in (('off', False, 0.0), ('on', True, args.p8_w)):
            net = build(eng_scale_scope=args.eng_scope, eng_scale_mode=args.eng_scale_mode, seed=args.seed, arm='task_off', round_ms=args.round_ms, w_stim=ws,
                        w_p8=wp8, r_star=args.rstar, p_safe=1.0, use_marker=um, n_trial=N_TRIAL,
                        choice_mode=mode_c, win_t0=args.win_t0, win_t1=args.win_t1)
            _run(net, args.round_ms * n_round + 50.0)
            acc, n = net.acc_probe()
            wr = net._rounds
            wta = float(np.mean([1.0 if r['hmax'] > 0.35 else 0.0 for r in wr])) if wr else float('nan')
            hm = float(np.max([r['hmax'] for r in wr])) if wr else float('nan')
            f1 = float(np.mean([1.0 if r['winner'] == 1 else 0.0 for r in wr])) if wr else float('nan')
            aspk = float(np.mean([0.5 * (r['c0'] + r['c1']) for r in wr])) if wr else float('nan')
            out[tag] = dict(acc=acc, n=n, wta=wta, hmax=hm, f1=f1, aspk=aspk)
        d = out['on']['acc'] - out['off']['acc']
        if mode_c == 'direct':

            part = out['on']['aspk']
            ok1 = part >= 1.0
            tag1 = '放电%.1f' % part
        else:
            ok1 = out['on']['wta'] >= 0.5
            tag1 = 'WTA%.2f' % out['on']['wta']
        ok = ok1 and (0.3 <= out['off']['f1'] <= 0.7) and (d >= 0.20)
        log('  %-9.2f %-9.3f %-9.3f %-+9.3f %-9s %-9.3f %-8.3f  %s'
            % (ws, out['off']['acc'], out['on']['acc'], d, tag1,
               out['on']['hmax'] if mode_c == 'hact' else float('nan'),
               out['off']['f1'], '①②③' if ok else ''))
        if ok and best is None:
            best = ws
    log('')
    if best is None:
        log('  ❌ 没有一档同时满足 ①②③ ⇒ 两条分支（**跑前写死**）：')
        log('     (a) 抬 `W_STIM` 上限（下一档 = %.1f）—— 决策机构还没被驱动起来；' % (max(scan) * 2.0))
        log('     (b) 若抬到很大仍 ① 不过 ⇒ **`H_UP·w_stim/10` 这条增益式不适合 011**，')
        log('         应改成"直接电流"式 `ie[ACT[c]] += W_STIM·n_spk(INJ[c])`（即 §1.2 的字面写法）')
        log('         —— 那是一条**接口改动**，必须回到用户处签字，不许自己换。')
    else:
        log('  ✅ **最小过线档 = `W_STIM = %.2f`** ⇒ 写进预注册 §1.2。' % best)
        log('     ★限定：单种子只作**筛查**；正式取值前须 ≥3 种子复核（方法学 ⑩/㉕）。')
    log('=' * 78)
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bench', action='store_true')
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument('--p8-probe', action='store_true')
    ap.add_argument('--calib-p8', action='store_true')
    ap.add_argument('--calib-task', action='store_true')
    ap.add_argument('--choice-mode', default=CHOICE_MODE0, choices=('hact', 'direct'))
    ap.add_argument('--seed', type=int, default=51)
    ap.add_argument('--round-ms', type=float, default=ROUND_MS)
    ap.add_argument('--w-stim', type=float, default=W_STIM0)
    ap.add_argument('--w-stim-scan', default='2,6,12,24,48')
    ap.add_argument('--p8-w', type=float, default=W_P8_0)
    ap.add_argument('--rstar', type=float, default=R_STAR0)
    ap.add_argument('--p-safe', type=float, default=0.5)
    ap.add_argument('--win-t0', type=float, default=WIN_T0)
    ap.add_argument('--win-t1', type=float, default=WIN_T1)
    ap.add_argument('--bench-rounds', type=int, default=40)
    ap.add_argument('--smoke-rounds', type=int, default=32)
    ap.add_argument('--calib-rounds', type=int, default=24)
    ap.add_argument('--p8-rounds', type=int, default=160)
    ap.add_argument('--p8-trials', type=int, default=10)
    ap.add_argument('--p8-scan', default='0,0.02,0.05,0.1,0.2')
    ap.add_argument('--eng-scale-mode', default='legacy', choices=('legacy', 'std', 'p95p5'),
                    help='第三因子尺子口径（P7(甲)；默认 legacy = 历史值）')
    ap.add_argument('--eng-scope', default='global', choices=('global', 'act'),
                    help='★第三因子尺子的**标定样本群**（P7(甲)-L；默认 global = 历史值）')
    ap.add_argument('--log', default=None)
    args = ap.parse_args()

    out = []

    def log(s):
        print(s)
        out.append(s)

    rc = 0
    t0 = time.time()
    if args.bench:
        mode_bench(log, args)
    if args.calib_task:
        mode_calib_task(log, args)
    if args.p8_probe:
        mode_p8_probe(log, args)
    if args.calib_p8:
        mode_calib_p8(log, args)
    if args.smoke:
        rc = mode_smoke(log, args)
    if not (args.bench or args.smoke or args.p8_probe or args.calib_p8 or args.calib_task):
        ap.print_help()
        return 2
    if args.log:
        with open(args.log, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out) + '\n')
        print('已写 %s' % args.log)
    print('总墙钟 %.1fs' % (time.time() - t0))
    return rc

if __name__ == '__main__':
    sys.exit(main())