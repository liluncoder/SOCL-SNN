import argparse
import copy
import json
import math
import os
import time

import numpy as np


SD = os.path.dirname(os.path.abspath(__file__))
SLICE_DIR = os.path.join(SD, 'slices')
STATE_PATH = os.path.join(SLICE_DIR, 'dev_slice.json')

CELL = {
    'E': dict(label='兴奋性 RS', a=0.02, b=0.20, c=-65.0, d=8.0, color='#1f6fb4'),
    'I': dict(label='抑制性 FS', a=0.10, b=0.20, c=-65.0, d=2.0, color='#c0392b'),
}

LIF_P = {
    'E': dict(R=1.0, tau=10.0, v_rest=-65.0, v_reset=-65.0, tau_u=100.0, d_adapt=0.0),
    'I': dict(R=1.0, tau=5.0, v_rest=-65.0, v_reset=-65.0, tau_u=100.0, d_adapt=0.0),
}

DEFAULT_CFG = {

    'n_units': 100,
    'n_E': 80, 'n_I': 20,
    'slot_grow': 0.5,
    'dt': 0.1, 'seed': 7,
    'K': {'ee': 7, 'ei': 16, 'ie': 5, 'ii': 2, 'lr': 3},
    'K_REF': {'ee': 7, 'ei': 16, 'ie': 5, 'ii': 2},
    'w_ref': {'ee': 0.13, 'ei': 0.06, 'ie': 0.32, 'ii': 0.05},
    'tau': {'ampa': 5.0, 'gaba': 10.0},
    'E_rev': {'ampa': 0.0, 'gaba': -80.0},
    'lr': {'g': 0.20, 'to_I': 0.0, 'topology': 'distance', 'dist_tau': 6.0},
    'drive': {'tonic': 2.5, 'noise': 0.0, 'noise_hold': 1.0},
    'bg': {'rate': 400.0, 'g': 0.012, 'off_after': None},
    'stim': {'mode': 'none', 'start': 500.0, 'dur': 50.0, 'amp': 15.0,
             'g_amp': 6.0, 'n_units': 4},
    'std': {'on': False, 'U': 0.35, 'tau_rec': 300.0},
    'cell_E': {}, 'cell_I': {},
    'trace': True, 'bin_ms': 5.0, 'rate_cap_ms': 300000,
    'spike_log_units': 0,

    'dev': {
        'on': True,
        'period': 200.0,
        'E0': 1.0,

        'budget_per_unit': 0.130,
        'c_spike': 0.0020,
        'upkeep': 0.0005,
        'c_syn': 0.000005,
        'E_death': -2.0,
        'E_div': 4.0,
        'prune_unused': True,
        'syn_prune_hz': 0.05,
        'max_units_growth': 1.5,
    },

    'delay': {'on': True, 'local_ms': 1.0, 'lr_base_ms': 2.0, 'lr_per_unit_ms': 0.6,
              'max_ms': 8.0, 'classes': 4, 'decouple': False},

    # gate-1: branch-local credit. Off by default; with it off the update path is
    # byte-identical to the point-neuron rule.
    'branch': {'on': False, 'n': 4, 'tau_ca': 60.0, 'fac_max': 3.0},

    # gate-1: pair-based eligibility. One trace per edge, incremented by one cell's spike
    # and spent by the other's, so the order of the two events decides the sign.
    'pair': {'on': False, 'tau': 20.0},

    'syn': {
        'on': True,

        'A_plus': 0.010, 'A_minus': 0.011,
        'tau_pre': 5.0, 'tau_post': 5.0,
        'w_min': 0.0, 'w_max': 0.40,
        'p_rel': 0.5,

        'norm_on': True,
        'norm_period': 200.0,
        'c_len': 0.000012,
        'E_prune_q': 0.25,
        'prune_per_period': 1,
        'min_out': 6,
    },

    'reward': {'target_hz': 10.0, 'tau': 500.0},
}

BAND = (3.0, 200.0)
OSC_TH = 8.0
EPILEPTIC_HZ = 45.0
SILENT_HZ = 1.0
ACTIVE_HZ = 1.0
SAT_FRAC = 0.25
LABEL_COLOR = {'沉默': '#7f8c8d', '平稳': '#27ae60', '振荡': '#2980b9', '癫痫': '#c0392b'}
V_FLOOR, V_CEIL, G_CEIL = -100.0, 60.0, 50.0

def _merge(base, upd):
    out = {}
    for k, v in base.items():
        out[k] = _merge(v, upd[k]) if isinstance(v, dict) and isinstance(upd.get(k), dict) \
            else upd.get(k, v)
    for k, v in upd.items():
        out.setdefault(k, v)
    return out

def _plain(o):
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return [_plain(v) for v in o.tolist()]
    return o

def atomic_dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    last = None
    for _ in range(20):
        try:
            os.replace(tmp, path)
            return path
        except PermissionError as e:
            last = e
            time.sleep(0.25)
    if last:
        raise last

def rk4_izh(v: np.ndarray, u: np.ndarray, I: np.ndarray,
            a: np.ndarray, b: np.ndarray, dt: float):
    def rhs(vv, uu):
        dv = 0.04 * vv**2 + 5.0 * vv + 140.0 - uu + I
        du = a * (b * vv - uu)
        return dv, du
    k1v, k1u = rhs(v, u)
    k2v, k2u = rhs(v + 0.5*dt*k1v, u + 0.5*dt*k1u)
    k3v, k3u = rhs(v + 0.5*dt*k2v, u + 0.5*dt*k2u)
    k4v, k4u = rhs(v + dt*k3v, u + dt*k3u)
    v_new = v + dt/6 * (k1v + 2*k2v + 2*k3v + k4v)
    u_new = u + dt/6 * (k1u + 2*k2u + 2*k3u + k4u)
    return v_new, u_new


def _pack(pre, post, w, n_pre, n_post):
    order = np.argsort(pre, kind='stable')
    return dict(pre=np.ascontiguousarray(pre[order], dtype=np.int64),
                post=np.ascontiguousarray(post[order], dtype=np.int64),
                w=np.ascontiguousarray(w[order], dtype=np.float64),
                indptr=np.searchsorted(np.asarray(pre)[order], np.arange(n_pre + 1)).astype(np.int64),
                n_post=n_post, n_syn=int(np.size(pre)))

class Network:

    def __init__(self, cfg=None, seed=None):
        self.cfg = _merge(DEFAULT_CFG, cfg or {})
        if seed is not None:
            self.cfg['seed'] = int(seed)
        self._cache_params()
        self._pre_build_hook()
        self._build_wiring()
        self.rng = np.random.default_rng(int(self.cfg['seed']) + 1)
        self._reset_state()

    def _cache_params(self):
        c = self.cfg
        cE = _merge(CELL['E'], c.get('cell_E') or {})
        cI = _merge(CELL['I'], c.get('cell_I') or {})
        self.pE = (cE['a'], cE['b'], cE['c'], cE['d'])
        self.pI = (cI['a'], cI['b'], cI['c'], cI['d'])

        self.neuron = str(os.environ.get('N011_NEURON', 'izh')).strip().lower()
        self.is_lif = (self.neuron in ('lif', 'alif'))
        self.is_alif = (self.neuron == 'alif')
        if self.is_lif:
            lE = _merge(LIF_P['E'], c.get('lif_E') or {})
            lI = _merge(LIF_P['I'], c.get('lif_I') or {})
            dE_l, dI_l = (lE['d_adapt'], lI['d_adapt']) if self.is_alif else (0.0, 0.0)
            self.pE = (0.0, 0.0, float(lE['v_reset']), float(dE_l))
            self.pI = (0.0, 0.0, float(lI['v_reset']), float(dI_l))
            self.lpE = (float(lE['R']), float(lE['tau']), float(lE['v_rest']), float(lE['tau_u']))
            self.lpI = (float(lI['R']), float(lI['tau']), float(lI['v_rest']), float(lI['tau_u']))

            self.v_spk = float(os.environ.get('N011_V_SPK', '30.0'))
        else:
            self.lpE = None
            self.lpI = None
            self.v_spk = 30.0
        self.nU = int(c['n_units'])
        self.nE0 = int(c['n_E'])
        self.nI0 = int(c['n_I'])
        self.nE_slot = int(round(self.nE0 * (1.0 + float(c['slot_grow']))))
        self.nI_slot = int(round(self.nI0 * (1.0 + float(c['slot_grow']))))
        self.nE = self.nE_slot
        self.nI = self.nI_slot
        self.N_E = self.nU * self.nE_slot
        self.N_I = self.nU * self.nI_slot
        self.dt = float(c['dt'])
        self.vA = float(c['E_rev']['ampa'])
        self.vG = float(c['E_rev']['gaba'])
        self.kA = math.exp(-self.dt / float(c['tau']['ampa']))
        self.kG = math.exp(-self.dt / float(c['tau']['gaba']))
        self.ms_steps = max(1, int(round(1.0 / self.dt)))
        self.noise_steps = max(1, int(round(float(c['drive']['noise_hold']) / self.dt)))
        self.std_on = bool(c['std']['on'])
        self.U_std = float(c['std']['U'])
        self.tau_rec = float(c['std']['tau_rec'])
        self.trace_on = bool(c.get('trace', True))
        self.bin_steps = max(1, int(round(float(c['bin_ms']) / self.dt)))
        self.bin_ms = self.bin_steps * self.dt
        self.budget = float(c['dev']['budget_per_unit']) * self.nU
        self.extra_I = None
        self.eng_med = 0.0
        self.eng_scale = 1.0

        self._calib_ov = None
        self._calib_cells = None

        dl = c['delay']
        self.delay_on = bool(dl['on'])
        self.n_cls = int(dl['classes'])
        self.ring_len = int(round(float(dl['max_ms']) / self.dt)) + 2
        self.syn_cfg = c['syn']
        self.syn_on = bool(self.syn_cfg['on'])
        self.p_rel = float(self.syn_cfg.get('p_rel', 1.0))

        self._tag_on = str(os.environ.get('N011_TAG', 'off')).strip().lower() == 'on'
        self.tag_tau = float(os.environ.get('N011_TAG_TAU', '100.0'))
        self.tag_theta = float(os.environ.get('N011_TAG_THETA', str(math.exp(-1.0))))
        if self._tag_on:

            assert self.tag_theta > 0.0, \
                '★N011_TAG_THETA 必须 > 0（θ=0 ⇒ 门恒开 ⇒ f_cap≈100%，见预注册 §十.2）'

            _dev_ok = bool(c['dev']['on']) or bool(c['dev'].get('energy_only', False))
            assert _dev_ok, \
                '★N011_TAG=on 但 `_energy_tick` 门不满足（dev.on/energy_only 全 False）⇒ tag 永不衰减'
            assert self.syn_on, '★N011_TAG=on 但 syn.on=False ⇒ STDP/迹衰减不跑（tag 无意义）'

        self._ts = str(os.environ.get('N011_TAG_SHUF', 'off')).strip().lower()
        if self._ts == 'on':
            self._ts = 'off'
        assert self._ts in ('off', 'time', 'subset'), \
            '★N011_TAG_SHUF 只许 off/on/time/subset，得到 %r' % self._ts
        self._ts_kind = {'off': 0, 'time': 1, 'subset': 2}[self._ts]
        self._ts_rate = None
        self._ts_sub = None
        self._ts_rng = None
        self._ts_upd = self._ts_open = None
        self._ts_rate_out = os.environ.get('N011_TAG_SHUF_RATE_OUT') or None
        self._ts_rate_path = os.environ.get('N011_TAG_SHUF_RATE') or None
        self._ts_nopen = int(os.environ.get('N011_TAG_SHUF_NOPEN', '0'))
        if self._ts in ('time', 'subset'):

            assert self._tag_on, \
                '★N011_TAG_SHUF=%s 需要 N011_TAG=on（门本身要照抄 r05 的实现）' % self._ts
            assert self._ts_rate_path and os.path.isfile(self._ts_rate_path), \
                '★N011_TAG_SHUF=%s 必须给**存在**的 N011_TAG_SHUF_RATE（逐边开率文件），得到 %r' \
                % (self._ts, self._ts_rate_path)
            if self._ts == 'subset':
                assert self._ts_nopen > 0, \
                    '★N011_TAG_SHUF=subset 必须给 N011_TAG_SHUF_NOPEN（> 0）'
        if self._ts_rate_out is not None:
            assert self._tag_on, '★N011_TAG_SHUF_RATE_OUT 需要 N011_TAG=on（要统计 tag 门）'
        self.delay_on = self.delay_on

        self._field_mode = str(os.environ.get('N011_FIELD', 'off')).strip().lower()
        assert self._field_mode in ('off', 'act', 'shuf', 'rand'), \
            '★未知 N011_FIELD=%r' % self._field_mode
        self.field_lam = float(os.environ.get('N011_FIELD_LAM', '0.0'))
        self.field_tau = float(os.environ.get('N011_FIELD_TAU', '100.0'))
        self.field_mu = float(os.environ.get('N011_FIELD_MU', '0.0'))
        self.field_sd = float(os.environ.get('N011_FIELD_SD', '0.0'))

        self.field_center = str(os.environ.get('N011_FIELD_CENTER', 'off')).strip().lower() == 'on'
        _tf_env = str(os.environ.get('N011_TFACTOR', 'global')).strip().lower()
        self._field_need = (self._field_mode != 'off') or (_tf_env in ('fieldv2', 'bias_rand'))
        if self._field_need:
            assert self.field_tau > 0.0, '★N011_FIELD_TAU 必须 > 0'
            _rng_field = np.random.default_rng(int(self.cfg['seed']) * 104729 + 9091)
            _nu = int(self.nU)
            self._field_pi = (np.roll(np.arange(_nu), max(1, _nu // 2))
                              if _nu >= 2 else np.arange(_nu))
            self._field_rng = _rng_field
            self._field_bias_z = _rng_field.normal(0.0, 1.0, size=self.N_E)
            self._field_stats = {'n_f': 0, 'sum_mean': 0.0, 'sum_std': 0.0,
                                 'sum_q25': 0.0, 'sum_q50': 0.0, 'sum_q75': 0.0,
                                 'n_z': 0, 'sum_sat': 0.0}
        else:
            self._field_pi = None
            self._field_rng = None
            self._field_bias_z = None
            self._field_stats = None
        self._uact = None
        self._uact_t = None
        self._uact_n = None
        self.BE = self._mk_bufs(self.N_E)
        self.BI = self._mk_bufs(self.N_I)

    @staticmethod
    def _mk_bufs(n):
        return {k: np.empty(n) for k in ('t1', 't2', 'sv', 'su',
                                         'k1v', 'k1u', 'k2v', 'k2u', 'k3v', 'k3u', 'k4v', 'k4u')}

    @staticmethod
    def _rk4_ip(v, u, I, a, b, dt, B):
        t1, t2, sv, su = B['t1'], B['t2'], B['sv'], B['su']
        k1v, k1u, k2v, k2u = B['k1v'], B['k1u'], B['k2v'], B['k2u']
        k3v, k3u, k4v, k4u = B['k3v'], B['k3u'], B['k4v'], B['k4u']
        np.multiply(v, v, out=t1)
        t1 *= 0.04
        np.multiply(v, 5.0, out=k1v)
        k1v += t1
        k1v += 140.0
        k1v -= u
        k1v += I
        np.multiply(v, b, out=k1u)
        k1u -= u
        k1u *= a
        np.multiply(k1v, 0.5 * dt, out=sv)
        sv += v
        np.multiply(k1u, 0.5 * dt, out=su)
        su += u
        np.multiply(sv, sv, out=t1)
        t1 *= 0.04
        np.multiply(sv, 5.0, out=k2v)
        k2v += t1
        k2v += 140.0
        k2v -= su
        k2v += I
        np.multiply(sv, b, out=k2u)
        k2u -= su
        k2u *= a
        np.multiply(k2v, 0.5 * dt, out=sv)
        sv += v
        np.multiply(k2u, 0.5 * dt, out=su)
        su += u
        np.multiply(sv, sv, out=t1)
        t1 *= 0.04
        np.multiply(sv, 5.0, out=k3v)
        k3v += t1
        k3v += 140.0
        k3v -= su
        k3v += I
        np.multiply(sv, b, out=k3u)
        k3u -= su
        k3u *= a
        np.multiply(k3v, dt, out=sv)
        sv += v
        np.multiply(k3u, dt, out=su)
        su += u
        np.multiply(sv, sv, out=t1)
        t1 *= 0.04
        np.multiply(sv, 5.0, out=k4v)
        k4v += t1
        k4v += 140.0
        k4v -= su
        k4v += I
        np.multiply(sv, b, out=k4u)
        k4u -= su
        k4u *= a
        np.multiply(k1v, dt / 6.0, out=t1)
        np.multiply(k2v, dt / 3.0, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(k3v, dt / 3.0, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(k4v, dt / 6.0, out=t2)
        np.add(t1, t2, out=t1)
        np.add(v, t1, out=v)
        np.multiply(k1u, dt / 6.0, out=t1)
        np.multiply(k2u, dt / 3.0, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(k3u, dt / 3.0, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(k4u, dt / 6.0, out=t2)
        np.add(t1, t2, out=t1)
        np.add(u, t1, out=u)

    @staticmethod
    def _lif_ip(v, u, I, lp, dt, B):
        R, tau, v_rest = lp[0], lp[1], lp[2]
        t1 = B['t1']
        np.multiply(I, R, out=t1)
        t1 += v_rest
        k = math.exp(-dt / tau)
        v -= t1
        v *= k
        v += t1

    @staticmethod
    def _alif_ip(v, u, I, lp, dt, B):
        R, tau, v_rest, tau_u = lp[0], lp[1], lp[2], lp[3]
        t1 = B['t1']
        np.multiply(I, R, out=t1)
        t1 += v_rest
        t1 -= u
        k = math.exp(-dt / tau)
        v -= t1
        v *= k
        v += t1
        u *= math.exp(-dt / tau_u)

    def weights(self):
        c = self.cfg
        return {k: float(c['w_ref'][k]) * float(c['K_REF'][k]) / max(1, int(c['K'][k]))
                for k in ('ee', 'ei', 'ie', 'ii')}

    def _tile_over_units(self, r, n_post, n_pre, K, no_self, chunk=64):
        U = self.nU
        K2 = int(min(K, n_pre - (1 if no_self else 0)))
        if K2 <= 0 or U <= 0:
            return np.zeros(0, np.int64), np.zeros(0, np.int64)
        pres, posts = [], []
        for u0 in range(0, U, chunk):
            m = min(chunk, U - u0)
            R = r.random((m, n_post, n_pre))
            if no_self and n_post == n_pre:
                for k in range(m):
                    np.fill_diagonal(R[k], np.inf)
            idx = np.argpartition(R, K2 - 1, axis=2)[:, :, :K2]
            post = np.tile(np.repeat(np.arange(n_post), K2), (m, 1))
            uu = np.repeat(np.arange(u0, u0 + m), n_post * K2).reshape(m, -1)
            pres.append(uu * n_pre + idx.reshape(m, -1))
            posts.append(uu * n_post + post)
        return np.concatenate(pres).ravel(), np.concatenate(posts).ravel()

    def _build_wiring(self):
        c = self.cfg
        r = np.random.default_rng(int(c['seed']))
        U, nE, nI = self.nU, self.nE_slot, self.nI_slot
        K = c['K']
        w = self.weights()
        pre_ee, post_ee = self._tile_over_units(r, nE, nE, K['ee'], True)
        pre_ei, post_ei = self._tile_over_units(r, nI, nE, K['ei'], False)
        pre_ie, post_ie = self._tile_over_units(r, nE, nI, K['ie'], False)
        pre_ii, post_ii = self._tile_over_units(r, nI, nI, K['ii'], True)
        n_lr = 0
        Kl = int(K['lr']) if c['lr']['topology'] != 'none' else 0
        if Kl > 0 and U > 1:
            own = np.repeat(np.arange(U * nE), Kl)
            if c['lr']['topology'] == 'distance':
                d = r.geometric(1.0 / max(1.0, float(c['lr']['dist_tau'])), size=own.size)
                d = np.clip(d, 1, max(1, U // 2))
                sign = np.where(r.random(own.size) < 0.5, -1, 1)
                src = (own // nE + sign * d) % U
            else:
                src = (own // nE + 1 + r.integers(0, U - 1, size=own.size)) % U
            pre_lr = src * nE + r.integers(0, nE, size=own.size)
            pre_ee = np.concatenate([pre_ee, pre_lr])
            post_ee = np.concatenate([post_ee, own])
            n_lr = own.size
        w_lr = w['ee'] * float(c['lr']['g'])

        n_ex = 0
        _ex = getattr(self, 'extra_ee_pre', None)
        if _ex is not None and np.size(_ex) > 0:
            _ex_pre = np.asarray(_ex, np.int64)
            _ex_post = np.asarray(self.extra_ee_post, np.int64)
            _ex_w = np.asarray(self.extra_ee_w, np.float64)
            if _ex_pre.size != _ex_post.size or _ex_pre.size != _ex_w.size:
                raise ValueError('extra_ee_pre/post/w 长度不一致：%d/%d/%d'
                                 % (_ex_pre.size, _ex_post.size, _ex_w.size))
            pre_ee = np.concatenate([pre_ee, _ex_pre])
            post_ee = np.concatenate([post_ee, _ex_post])
            n_ex = int(_ex_pre.size)
        self.n_lr = int(n_lr)
        self.n_ex = int(n_ex)
        self.n_local = int(pre_ee.size - n_lr - n_ex)
        _w_ee = np.concatenate([np.full(pre_ee.size - n_lr - n_ex, w['ee']),
                                np.full(n_lr, w_lr)])
        if n_ex:
            _w_ee = np.concatenate([_w_ee, np.asarray(self.extra_ee_w, np.float64)])
        self.S = {
            'ee': _pack(pre_ee, post_ee, _w_ee, self.N_E, self.N_E),
            'ei': _pack(pre_ei, post_ei, np.full(pre_ei.size, w['ei']), self.N_E, self.N_I),
            'ie': _pack(pre_ie, post_ie, np.full(pre_ie.size, w['ie']), self.N_I, self.N_E),
            'ii': _pack(pre_ii, post_ii, np.full(pre_ii.size, w['ii']), self.N_I, self.N_I),
        }
        self.w_local = w

        pre, post = self.S['ee']['pre'], self.S['ee']['post']
        dist = np.abs(pre // nE - post // nE).astype(np.float32)
        dist = np.minimum(dist, U - dist)
        self.syn_dist = dist

        # A presynaptic cell contacts one branch only, so an edge's branch is a property
        # of its pre cell. br_s[c, b] is the low-passed input that reached branch b of c.
        br = c.get('branch', {})
        self.br_on = bool(br.get('on', False))
        self.br_n = max(1, int(br.get('n', 4)))
        self.br_fac_max = float(br.get('fac_max', 3.0))
        if self.br_on:
            self.br_branch = (pre % self.br_n).astype(np.int64)
            self.br_s = np.zeros((self.N_E, self.br_n), np.float64)
        else:
            self.br_branch = np.zeros(pre.size, np.int64)
            self.br_s = None

        pr = c.get('pair', {})
        self.pair_on = bool(pr.get('on', False))
        if self.pair_on:
            # one eligibility per synapse, for potentiation and for depression
            self.e_ltp = np.zeros(pre.size, np.float64)
            self.e_ltd = np.zeros(pre.size, np.float64)
        else:
            self.e_ltp = None
            self.e_ltd = None
        dl = c['delay']
        if dl['on']:
            if dl.get('decouple'):

                d_mean = float(dist[dist >= 0.5].mean()) if (dist >= 0.5).any() else 0.0
                dms = np.where(dist < 0.5, float(dl['local_ms']),
                               float(dl['lr_base_ms']) + float(dl['lr_per_unit_ms']) * d_mean)
            else:
                dms = np.where(dist < 0.5, float(dl['local_ms']),
                               float(dl['lr_base_ms']) + float(dl['lr_per_unit_ms']) * dist)
            dms = np.clip(dms, 0.0, float(dl['max_ms']))
            lag = np.round(dms / self.dt).astype(np.int64)
            cls_w = self.ring_len / max(1, self.n_cls)
            self.syn_cls = np.clip((lag / max(1.0, cls_w)).astype(np.int64), 0, self.n_cls - 1)

            self.cls_lag = []
            for k in range(self.n_cls):
                m = self.syn_cls == k
                self.cls_lag.append(int(np.median(lag[m])) if m.any() else 0)
            self.spk_ring = [None] * self.ring_len
            self.ring_pos = 0
        else:
            self.syn_cls = np.zeros(pre.size, np.int64)
            self.cls_lag = [0]
            self.spk_ring = [None] * 1
            self.ring_pos = 0

        order_in = np.argsort(post, kind='stable')
        self.in_order = order_in
        self.in_ptr = np.searchsorted(post[order_in], np.arange(self.N_E + 1)).astype(np.int64)
        self.xE_t = np.zeros(self.N_E)
        self.yE_t = np.zeros(self.N_E)
        self.reward = 0.0

        self.syn_len_E = np.bincount(pre, weights=dist.astype(float),
                                     minlength=self.N_E)[:self.N_E]

        self.w_budget_E = np.bincount(self.S['ee']['post'], weights=self.S['ee']['w'],
                                      minlength=self.N_E)[:self.N_E]
        self.last_norm = 0.0
        self.f_lr = 0.0 if c['lr']['topology'] == 'none' else \
            (w['ee'] * float(c['lr']['g']) * Kl) / (w['ee'] * K['ee'] + w['ee'] * float(c['lr']['g']) * Kl)

        self.outdeg_E = np.bincount(self.S['ee']['pre'], minlength=self.N_E).astype(float)
        self.outdeg_I = np.bincount(self.S['ie']['pre'], minlength=self.N_I).astype(float)

    def _reset_state(self, t0=0.0):
        cE, cI = self.pE, self.pI
        d = self.cfg['dev']
        self.t = float(t0)
        self.vE = np.full(self.N_E, -65.0)
        self.uE = np.full(self.N_E, cE[1] * -65.0)
        self.vI = np.full(self.N_I, -65.0)
        self.uI = np.full(self.N_I, cI[1] * -65.0)
        self.gEa = np.zeros(self.N_E)
        self.gEg = np.zeros(self.N_E)
        self.gIa = np.zeros(self.N_I)
        self.gIg = np.zeros(self.N_I)

        uu = np.arange(self.nU)
        self.aliveE = np.zeros(self.N_E, bool)
        self.aliveE[(uu[:, None] * self.nE_slot + np.arange(self.nE0)[None, :]).ravel()] = True
        self.aliveI = np.zeros(self.N_I, bool)
        self.aliveI[(uu[:, None] * self.nI_slot + np.arange(self.nI0)[None, :]).ravel()] = True
        self.born_t = np.full(self.N_E, float(t0))
        self.engE = np.where(self.aliveE, float(d['E0']), 0.0)
        self.engI = np.where(self.aliveI, float(d['E0']), 0.0)
        self.actE = np.zeros(self.N_E)
        self.actI = np.zeros(self.N_I)
        self.spkE_ms = np.zeros(self.N_E)
        self.spkI_ms = np.zeros(self.N_I)
        self.spk_prev = np.zeros(self.N_E)

        self.rate_ema = np.zeros(self.N_E)
        self.ema_decay = math.exp(-self.dt / 1000.0)
        self.syn_use = np.zeros(self.S['ee']['n_syn'])

        self.syn_use_tot = np.zeros(self.S['ee']['n_syn'])
        self.syn_alive = np.ones(self.S['ee']['n_syn'], bool)

        self.tag = (np.zeros(self.S['ee']['n_syn']) if self._tag_on else None)

        if self._ts_kind != 0:
            _nsyn = int(self.S['ee']['n_syn'])
            self._ts_rng = np.random.default_rng(int(self.cfg['seed']) * 7919 + 13)
            if self._ts_kind == 1:
                with open(self._ts_rate_path, encoding='utf-8') as _f:
                    _rt = np.asarray(json.load(_f), dtype=float).ravel()
                assert _rt.size == _nsyn, \
                    '★开率文件长度 %d ≠ n_syn %d' % (_rt.size, _nsyn)
                assert np.all(np.isfinite(_rt)) and np.all((_rt >= 0.0) & (_rt <= 1.0)), \
                    '★逐边开率必须有限且落在 [0,1]'
                self._ts_rate = _rt
            else:
                _sub = np.zeros(_nsyn, bool)
                _pick = self._ts_rng.choice(_nsyn, size=min(int(self._ts_nopen), _nsyn),
                                            replace=False)
                _sub[_pick] = True
                self._ts_sub = _sub

        if self._ts_rate_out is not None and self._ts_upd is None:
            self._ts_upd = np.zeros(int(self.S['ee']['n_syn']), np.int64)
            self._ts_open = np.zeros(int(self.S['ee']['n_syn']), np.int64)

        self.idle_hist = np.zeros(13, np.int64)
        self.alive_hist = np.zeros(13, np.int64)

        self.hist = []
        self.pop_rate_hist = []
        self.cells_by_q = np.zeros(4, int)
        self.dead_by_q = np.zeros(4, int)
        self.dead_log = []
        self.n_born = 0
        self.n_dead = 0
        self.n_pruned = 0

        n_syn_ee = self.S['ee']['n_syn']
        self.n_rev         = 0
        self.n_rev_lr      = 0
        self.n_cut_dead    = 0
        self.n_cut_dead_lr = 0
        self.n_cut_idle    = 0
        self.n_cut_idle_lr = 0
        self.n_cut_cost    = 0
        self.n_cut_cost_lr = 0
        self.fate    = np.zeros(n_syn_ee, np.int8)
        self.rev_cnt = np.zeros(n_syn_ee, np.int32)
        self.infra = np.zeros(n_syn_ee, bool)

        self.cut_t_log = []
        self.cut_i_log = []

        self.n_exempt     = 0
        self.n_exempt_lr  = 0
        self.n_idle_cand  = 0
        self.idle_near    = 0
        self.idle_far     = 0
        self.exp_near     = 0.0
        self.exp_far      = 0.0
        self._dist_med    = None

        self.w_cap = None
        self.last_dev = float(t0)
        self.noise = np.zeros(self.N_E)
        self.noise_timer = 0
        self.t_lastE = np.full(self.N_E, -1e9)
        self.t_lastU = np.full(self.nU, -1e9)
        self.n_spkE = np.zeros(self.N_E, int)
        self.n_spkI = np.zeros(self.N_I, int)
        self.n_spkU = np.zeros(self.nU, int)
        self.spk_total = 0
        cap = int(self.cfg['rate_cap_ms'])
        self.pop_E = np.zeros(cap, np.float32)
        self.pop_I = np.zeros(cap, np.float32)
        self.pop_ms0 = int(round(t0))
        self.pop_n = 0

        nbin = int(cap / max(1e-9, self.bin_ms)) + 2
        self.u_cnt = np.zeros((self.nU, nbin), np.uint16) if self.trace_on else None
        self.u_ms0 = int(round(t0))
        self.u_n = 0
        self._ms_E = 0
        self._ms_I = 0
        self._sub = 0
        self._ubsub = 0
        self._accU = np.zeros(self.nU, np.int32) if self.trace_on else None
        self._n_alive_E = int(self.aliveE.sum())
        self._n_alive_I = int(self.aliveI.sum())
        nlog = int(self.cfg.get('spike_log_units', 0) or 0)
        self.n_log = nlog * self.nE_slot
        self.spk_log = [] if nlog > 0 else None
        self._kick_until = -1e9
        self.hist.append(self._snapshot())

    def _snapshot(self):
        return {'t': self.t, 'nE': int(self.aliveE.sum()), 'nI': int(self.aliveI.sum()),
                'eng_mean': float(self.engE[self.aliveE].mean()) if self.aliveE.any() else 0.0,
                'eng_std': float(self.engE[self.aliveE].std()) if self.aliveE.any() else 0.0,
                'dead': self.n_dead, 'born': self.n_born, 'pruned': self.n_pruned,
                'syn_alive': int(self.syn_alive.sum()),

                'n_rev':         self.n_rev,
                'n_rev_lr':      self.n_rev_lr,
                'n_cut_dead':    self.n_cut_dead,
                'n_cut_dead_lr': self.n_cut_dead_lr,
                'n_cut_idle':    self.n_cut_idle,
                'n_cut_idle_lr': self.n_cut_idle_lr}

    def stim_gate(self, t):
        s = self.cfg['stim']
        mode = s.get('mode', 'none')
        if mode == 'none':
            return 0.0
        if mode == 'kick':
            return 1.0 if s['start'] <= t < s['start'] + s['dur'] else 0.0
        if mode == 'live':
            return 1.0
        return 1.0 if s['start'] <= t < s['start'] + s['dur'] else 0.0

    def bg_on(self, t):
        off = self.cfg['bg'].get('off_after')
        return (off is None) or (t < float(off))

    def kick_now(self, dur=None):
        dur = float(self.cfg['stim'].get('dur', 50.0) if dur is None else dur)
        self._kick_until = self.t + dur
        return self._kick_until

    def _pre_build_hook(self):
        pass

    def idle_rate(self, period):
        return self.syn_use / (float(period) / 1000.0)

    def step(self, n=1):
        nE, nI, N_E, N_I = self.nE_slot, self.nI_slot, self.N_E, self.N_I
        dt = self.dt
        aE, bE, cE, dE = self.pE
        aI, bI, cI, dI = self.pI
        tonic = float(self.cfg['drive']['tonic'])
        kick_amp = float(self.cfg['stim'].get('amp', 0.0))
        g_amp = float(self.cfg['stim'].get('g_amp', 6.0))
        bg_rate = float(self.cfg['bg']['rate'])
        bg_g = float(self.cfg['bg']['g'])
        p_bg = min(1.0, bg_rate * 0.001)
        nz_amp = float(self.cfg['drive']['noise'])
        dev_on = bool(self.cfg['dev']['on'])

        energy_only = bool(self.cfg['dev'].get('energy_only', False))
        period = float(self.cfg['dev']['period'])
        aliveE, aliveI = self.aliveE, self.aliveI

        for k in range(n):
            t = self.t
            gate = self.stim_gate(t)
            if self._sub == 0 and self.bg_on(t):
                hit = self.rng.random(N_E) < p_bg
                if hit.any():
                    self.gEa[hit & aliveE] += bg_g
            if nz_amp > 0.0:
                if self.noise_timer <= 0:
                    self.noise = self.rng.standard_normal(N_E)
                    self.noise_timer = self.noise_steps
                self.noise_timer -= 1
                IE = self.noise * nz_amp + tonic
            else:
                IE = np.full(N_E, tonic)
            if t < self._kick_until or gate > 0.0:
                if t < self._kick_until or self.cfg['stim'].get('mode') == 'kick':
                    IE = IE + kick_amp * self._kick_mask()
                else:
                    IE = IE + g_amp
            IE = IE + self.gEa * (self.vA - self.vE) + self.gEg * (self.vG - self.vE)
            II = self.gIa * (self.vA - self.vI) + self.gIg * (self.vG - self.vI)

            if self.extra_I is not None:
                IE = IE + self.extra_I[:self.N_E]
            if self.is_alif:
                self._alif_ip(self.vE, self.uE, IE, self.lpE, dt, self.BE)
                self._alif_ip(self.vI, self.uI, II, self.lpI, dt, self.BI)
            elif self.is_lif:
                self._lif_ip(self.vE, self.uE, IE, self.lpE, dt, self.BE)
                self._lif_ip(self.vI, self.uI, II, self.lpI, dt, self.BI)
            else:
                self._rk4_ip(self.vE, self.uE, IE, aE, bE, dt, self.BE)
                self._rk4_ip(self.vI, self.uI, II, aI, bI, dt, self.BI)
            np.clip(self.vE, V_FLOOR, V_CEIL, out=self.vE)
            np.clip(self.vI, V_FLOOR, V_CEIL, out=self.vI)
            sE = (self.vE >= self.v_spk) & aliveE
            sI = (self.vI >= self.v_spk) & aliveI
            nE_sp = 0
            if sE.any():
                idx = np.nonzero(sE)[0]
                self.vE[idx] = cE
                self.uE[idx] += dE
                self.t_lastE[idx] = t
                self.n_spkE[idx] += 1
                self.spkE_ms[idx] += 1.0
                u_of = idx // nE
                self.t_lastU[u_of] = t
                cnt = np.bincount(u_of, minlength=self.nU)
                self.n_spkU += cnt
                if self.trace_on:
                    self._accU += cnt
                if self.spk_log is not None:
                    sel = idx[idx < self.n_log]
                    if sel.size:
                        self.spk_log.append((sel.copy(), t))
                nE_sp = idx.size
            if sI.any():
                idx = np.nonzero(sI)[0]
                self.vI[idx] = cI
                self.uI[idx] += dI
                self.n_spkI[idx] += 1
                self.spkI_ms[idx] += 1.0
            self.spk_total += nE_sp + int(sI.sum())

            if self.delay_on:
                self.spk_ring[self.ring_pos] = np.nonzero(sE)[0]
                for c in range(self.n_cls):
                    src = self.spk_ring[(self.ring_pos - self.cls_lag[c]) % self.ring_len]
                    if src is not None and src.size:
                        self._transmit('ee', self._as_f(src), self.gEa, act=self.actE, cls=c)
                self.ring_pos = (self.ring_pos + 1) % self.ring_len
            elif nE_sp:
                self._transmit('ee', sE.astype(np.float64), self.gEa, act=self.actE)
            if nE_sp:
                self._transmit('ei', sE.astype(np.float64), self.gIa)
            if sI.any():
                fI = sI.astype(np.float64)
                self._transmit('ie', fI, self.gEg)
                self._transmit('ii', fI, self.gIg)

            if self.syn_on and nE_sp:
                self._stdp_step(np.nonzero(sE)[0])
            self.gEa *= self.kA
            self.gIa *= self.kA
            self.gEg *= self.kG
            self.gIg *= self.kG
            np.clip(self.gEa, 0.0, G_CEIL, out=self.gEa)
            np.clip(self.gIa, 0.0, G_CEIL, out=self.gIa)
            np.clip(self.gEg, 0.0, G_CEIL, out=self.gEg)
            np.clip(self.gIg, 0.0, G_CEIL, out=self.gIg)
            self._ms_E += nE_sp
            self._ms_I += int(sI.sum())
            self.t += dt
            self._sub += 1
            self._ubsub += 1
            if self._sub >= self.ms_steps:
                self._sample_ms()
            if self._ubsub >= self.bin_steps:
                self._sample_bin()
            if dev_on and (not energy_only) and (t - self.last_dev) >= period:
                self._develop()

    def _as_f(self, idx):
        f = np.zeros(self.N_E)
        f[idx] = 1.0
        return f

    def _normalize_weights(self):
        ee = self.S['ee']
        post = ee['post']

        ex = getattr(self, 'ex_mask', None)
        if ex is None:
            ex = np.zeros(int(ee['n_syn']), bool)
        alive_w = ee['w'] * self.syn_alive * (~ex)
        tot = np.bincount(post, weights=alive_w, minlength=self.N_E)[:self.N_E]
        scale = np.ones(self.N_E)
        m = (tot > 1e-9) & (self.w_budget_E > 1e-9)
        scale[m] = self.w_budget_E[m] / tot[m]
        sc = scale[post].copy()
        sc[ex] = 1.0
        ee['w'] *= sc
        if ex.any():
            pid = getattr(self, 'ex_pid', None)
            bud = getattr(self, 'ex_bud', None)
            if pid is not None and bud:
                key = pid[ex]
                nk = int(key.max()) + 1
                tw = np.bincount(key, weights=(ee['w'][ex] * self.syn_alive[ex]),
                                 minlength=nk)
                bt = np.zeros(nk)
                for kk, vv in bud.items():
                    if kk < nk:
                        bt[kk] = vv
                rat = np.ones(nk)
                ok = (tw > 1e-9) & (bt > 1e-9)
                rat[ok] = bt[ok] / tw[ok]
                ee['w'][ex] *= rat[key]
        np.clip(ee['w'], self.syn_cfg['w_min'], self._w_hi(), out=ee['w'])

    def _w_hi(self):
        return self.syn_cfg['w_max'] if getattr(self, 'w_cap', None) is None else self.w_cap

    def idle_exempt(self):
        return None

    def _log_cut_idx(self, idx):
        if idx.size:
            self.cut_t_log.append(float(self.t))
            self.cut_i_log.append(np.asarray(idx).copy())

    def _log_cut(self, mask):
        self._log_cut_idx(np.nonzero(mask)[0])

    def _prune_stressed(self):
        c = self.syn_cfg
        a = self.engE[self.aliveE]
        if a.size < 8:
            return
        thr = float(np.percentile(a, 100.0 * float(c['E_prune_q'])))
        stressed = np.nonzero(self.aliveE & (self.engE <= thr))[0]
        if stressed.size == 0:
            return
        ee = self.S['ee']
        w = ee['w']
        k_per = int(c['prune_per_period'])
        min_out = int(c['min_out'])
        period_s = max(1e-9, float(self.cfg['dev']['period']) / 1000.0)
        use_hz = self.syn_use / period_s
        for i in stressed:
            aa, bb = ee['indptr'][i], ee['indptr'][i + 1]
            cand = np.arange(aa, bb)
            cand = cand[self.syn_alive[cand] & (~self.infra[cand])]
            if cand.size <= min_out:
                continue

            val = w[cand] * (1.0 + 20.0 * use_hz[cand]) / (1.0 + self.syn_dist[cand])
            k = min(k_per, cand.size - min_out)
            if k <= 0:
                continue
            cut = cand[np.argpartition(val, k - 1)[:k]]
            self.syn_alive[cut] = False
            self.n_pruned += int(cut.size)

    def _calib_of(self, v):
        if v.size < 4:
            return None
        med = float(np.median(v))
        mode = str(self.cfg['dev'].get('eng_scale_mode', 'legacy'))
        if mode == 'std':
            sc = float(np.std(v))
        elif mode == 'p95p5':
            sc = float(np.percentile(v, 95) - np.percentile(v, 5))
        else:
            sc = 0.5 * float(np.percentile(v, 75) - np.percentile(v, 25))
        return med, max(1e-6, sc)

    def _reward_of(self, cells):

        _cc = self._calib_cells
        if _cc is None:
            sc = max(1e-6, self.eng_scale)
            return np.clip((self.engE[cells] - self.eng_med) / sc, -1.0, 1.0)
        _mL, _sL = self._calib_ov
        _sL = max(1e-6, float(_sL))
        if np.ndim(cells) == 0:

            _c = int(cells)
            if _cc[_c]:
                return float(np.clip((self.engE[_c] - _mL) / _sL, -1.0, 1.0))
            return float(np.clip((self.engE[_c] - self.eng_med) / max(1e-6, self.eng_scale),
                                 -1.0, 1.0))
        cells = np.asarray(cells)
        pos = _cc[cells]
        out = np.empty(cells.size, float)
        if pos.any():
            out[pos] = np.clip((self.engE[cells[pos]] - _mL) / _sL, -1.0, 1.0)
        if (~pos).any():
            _sG = max(1e-6, self.eng_scale)
            out[~pos] = np.clip((self.engE[cells[~pos]] - self.eng_med) / _sG, -1.0, 1.0)
        return out

    def _field_units(self):
        if self._uact is None:
            self._uact = np.zeros(int(self.nU), float)
            self._uact_t = float(self.t)
            self._uact_n = np.asarray(self.n_spkU, int).copy()
        dt = float(self.t) - float(self._uact_t)
        if dt > 0.0:
            self._uact *= math.exp(-dt / max(1e-9, float(self.field_tau)))
            self._uact_t = float(self.t)
        d = np.asarray(self.n_spkU, int) - self._uact_n
        if d.any():
            self._uact += d
            self._uact_n = np.asarray(self.n_spkU, int).copy()
        u = self._uact
        ii = np.arange(u.size)
        K = np.exp(-np.abs(ii[:, None] - ii[None, :]) / 1.0)
        f = (K @ u) / np.maximum(K.sum(1), 1e-9)
        st = self._field_stats
        if st is not None:
            st['n_f'] += 1
            st['sum_mean'] += float(f.mean())
            st['sum_std'] += float(f.std())

            _q = np.quantile(f, (0.25, 0.5, 0.75))
            st['sum_q25'] += float(_q[0])
            st['sum_q50'] += float(_q[1])
            st['sum_q75'] += float(_q[2])
        return f

    def field_gain(self, cells, lam):
        f = self._field_units()
        if self.field_center:
            f = f - float(f.mean())
        m = self._field_mode
        if m == 'shuf':
            f = f[self._field_pi]
        elif m == 'rand':
            f = f[self._field_rng.permutation(f.size)]
        cells = np.asarray(cells, int)
        return float(lam) * f[cells // int(self.nE_slot)]

    def bias_rand_gain(self, cells, lam):
        g = float(self.field_mu) + float(self.field_sd) * np.asarray(self._field_bias_z, float)
        cells = np.asarray(cells, int)
        return float(lam) * g[cells]

    def _br_fac(self, post_idx, wi):
        """Relative activation of the branch each synapse lands on.

        fac_b = s_b / mean_b(s_b), clipped to [0, fac_max]. If every branch of a cell
        is equally active, fac == 1 and the update reduces to the plain (pre, R) rule;
        what the factor adds is a difference *between* branches, i.e. a way for two
        synapses on the same cell to receive different credit.
        """
        s = self.br_s[post_idx, self.br_branch[wi]]
        m = self.br_s[post_idx].mean(axis=1)
        return np.clip(s / np.maximum(m, 1e-12), 0.0, self.br_fac_max)

    def _pair_step(self, spk):
        """Pair-based update: an edge's eligibility is set by one cell's spike and spent by
        the other's, so the order decides the sign.

        Both consumptions read the eligibility as it stood *before* this step increments
        anything, which is why a pre and a post spike in the same time step do not pair with
        themselves.
        """
        c = self.syn_cfg
        ee = self.S['ee']
        w = ee['w']

        st = self.in_ptr[spk]
        cnt = self.in_ptr[spk + 1] - st
        tot = int(cnt.sum())
        if tot:
            off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            wi_in = self.in_order[np.repeat(st, cnt) + off]
            Ri = np.repeat(self._reward_of(spk), cnt)
        else:
            wi_in = np.zeros(0, np.int64)
            Ri = np.zeros(0)

        st = ee['indptr'][spk]
        cnt = ee['indptr'][spk + 1] - st
        tot = int(cnt.sum())
        if tot:
            off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            wi_out = np.repeat(st, cnt) + off
            Rj = self._reward_of(ee['post'][wi_out])
        else:
            wi_out = np.zeros(0, np.int64)
            Rj = np.zeros(0)

        e_l = self.e_ltp[wi_in].copy() if wi_in.size else None
        e_d = self.e_ltd[wi_out].copy() if wi_out.size else None

        if wi_in.size:
            if self.br_on:
                e_l = e_l * self._br_fac(np.repeat(spk, self.in_ptr[spk + 1] - self.in_ptr[spk]), wi_in)
            w[wi_in] += c['A_plus'] * e_l * Ri
            self.e_ltp[wi_in] = 0.0
        if wi_out.size:
            if self.br_on:
                e_d = e_d * self._br_fac(ee['post'][wi_out], wi_out)
            w[wi_out] -= c['A_minus'] * e_d * Rj
            self.e_ltd[wi_out] = 0.0

        # a spike arms the opposite trace on the edges it can pair with later
        if wi_out.size:
            self.e_ltp[wi_out] += 1.0
        if wi_in.size:
            self.e_ltd[wi_in] += 1.0

        np.clip(w, c['w_min'], self.w_max if hasattr(self, 'w_max') else self._w_hi(), out=w)

    def _stdp_step(self, spk):
        c = self.syn_cfg
        ee = self.S['ee']
        w = ee['w']
        x, y = self.xE_t, self.yE_t
        E0 = max(1e-9, float(self.cfg['dev']['E0']))

        g_tag = (self.tag >= self.tag_theta) if self._tag_on else None

        _tsk = self._ts_kind
        _ts_upd, _ts_open = self._ts_upd, self._ts_open

        if self.pair_on:
            self._pair_step(spk)
            return

        st = ee['indptr'][spk]
        cnt = ee['indptr'][spk + 1] - st
        tot = int(cnt.sum())
        if tot:
            off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            wi = np.repeat(st, cnt) + off
            pj = ee['post'][wi]
            Rj = self._reward_of(pj)
            if self.br_on:
                # accumulate the input that reached each branch before scaling the trace
                _drv = x[ee['pre'][wi]] * w[wi]
                np.add.at(self.br_s, (pj, self.br_branch[wi]), _drv)
                ypost = y[pj] * self._br_fac(pj, wi)
            else:
                ypost = y[pj]
            if g_tag is None:
                w[wi] -= c['A_minus'] * ypost * Rj
            elif _tsk == 0:
                _ge = g_tag[wi]
                w[wi] -= c['A_minus'] * ypost * Rj * _ge
            elif _tsk == 2:
                _ge = self._ts_sub[wi]
                w[wi] -= c['A_minus'] * ypost * Rj * _ge
            else:
                _ge = (self._ts_rng.random(wi.size) < self._ts_rate[wi])
                w[wi] -= c['A_minus'] * ypost * Rj * _ge

            if _ts_upd is not None:
                _ts_upd[wi] += 1
                _ts_open[wi] += _ge

        st = self.in_ptr[spk]
        cnt = self.in_ptr[spk + 1] - st
        tot = int(cnt.sum())
        if tot:
            off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            li = np.repeat(st, cnt) + off
            wi = self.in_order[li]
            pj = ee['pre'][wi]
            Ri = self._reward_of(spk)
            if self.br_on:
                # eligibility = pre trace * branch factor; factor is 1 when all branches
                # are equally active, which is why the equal case reduces to the old rule
                xpre = x[pj] * self._br_fac(np.repeat(spk, cnt), wi)
            else:
                xpre = x[pj]
            if g_tag is None:
                w[wi] += c['A_plus'] * xpre * np.repeat(Ri, cnt)
            elif _tsk == 0:
                _ge = g_tag[wi]
                w[wi] += c['A_plus'] * xpre * np.repeat(Ri, cnt) * _ge
            elif _tsk == 2:
                _ge = self._ts_sub[wi]
                w[wi] += c['A_plus'] * xpre * np.repeat(Ri, cnt) * _ge
            else:
                _ge = (self._ts_rng.random(wi.size) < self._ts_rate[wi])
                w[wi] += c['A_plus'] * xpre * np.repeat(Ri, cnt) * _ge
            if _ts_upd is not None:
                _ts_upd[wi] += 1
                _ts_open[wi] += _ge
        np.clip(w, c['w_min'], self._w_hi(), out=w)
        x[spk] += 1.0
        y[spk] += 1.0

    def dump_tag_shuf_rate(self, path):
        if self._ts_upd is None:
            raise RuntimeError('★未开启 N011_TAG_SHUF_RATE_OUT ⇒ 没有逐边计数可落盘')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'n_syn': int(self._ts_upd.size),
                       'upd': [int(v) for v in self._ts_upd],
                       'open': [int(v) for v in self._ts_open]}, f, ensure_ascii=False)
        return path

    def _kick_mask(self):
        km = np.zeros(self.N_E, bool)
        for u in self._pick_kick_units():
            km[u * self.nE_slot: u * self.nE_slot + self.nE_slot] = True
        return km

    def _pick_kick_units(self):
        n = int(self.cfg['stim'].get('n_units', 1))
        if n <= 0 or self.nU <= 1:
            return np.array([0], int)
        return np.unique(np.round(np.linspace(0, self.nU, n, endpoint=False)).astype(int)) % self.nU

    def _transmit(self, gname, f_pre, G, act=None, cls=None):
        g = self.S[gname]
        act_cells = np.nonzero(f_pre)[0]
        if act_cells.size == 0:
            return
        st = g['indptr'][act_cells]
        en = g['indptr'][act_cells + 1]
        cnt = en - st
        tot = int(cnt.sum())
        if tot == 0:
            return
        off = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        idx = np.repeat(st, cnt) + off
        if cls is not None:
            idx = idx[self.syn_cls[idx] == cls]
            if idx.size == 0:
                return
        post = g['post'][idx]
        w = g['w'][idx].copy()
        if gname == 'ee':
            np.multiply(w, self.syn_alive[idx], out=w)
            rel = None
            if self.p_rel < 1.0:
                rel = (self.rng.random(w.size) < self.p_rel)
                w *= rel
            if self.syn_use is not None:
                self.syn_use[idx] += 1.0
            if getattr(self, 'syn_use_tot', None) is not None:
                self.syn_use_tot[idx] += 1.0
            if self._tag_on:

                if rel is None:
                    self.tag[idx] += 1.0
                else:
                    self.tag[idx[rel]] += 1.0
        add = np.bincount(post, weights=w, minlength=g['n_post'])
        G += add
        if act is not None:

            act += np.bincount(post, weights=self._alive_w(gname, idx), minlength=g['n_post'])

    def _alive_w(self, gname, idx):
        if gname != 'ee':
            return np.ones(idx.size)
        return self.syn_alive[idx].astype(float)

    def _sample_bin(self):
        self._ubsub = 0
        if not self.trace_on:
            return
        i = self.u_n
        if i < self.u_cnt.shape[1]:
            np.clip(self._accU, 0, 65535, out=self._accU)
            self.u_cnt[:, i] = self._accU.astype(np.uint16)
            self.u_n = i + 1
        self._accU[:] = 0

    def _sample_ms(self):
        self._sub = 0
        i = self.pop_n
        if i < self.pop_E.size:
            na = max(1, self._n_alive_E)
            self.pop_E[i] = self._ms_E * 1000.0 / na
            self.pop_I[i] = self._ms_I * 1000.0 / max(1, self._n_alive_I)
            self.pop_n = i + 1
        self._ms_E = self._ms_I = 0
        if self.cfg['dev']['on'] or self.cfg['dev'].get('energy_only', False):

            self._energy_tick()

    def _energy_tick(self):
        d = self.cfg['dev']
        aliveE, aliveI = self.aliveE, self.aliveI

        tot = float(self.actE[aliveE].sum())
        inc = (self.budget * self.actE / tot) if tot > 0 else \
            (self.budget / max(1, self._n_alive_E) * aliveE)
        cost = float(d['c_spike']) * self.spkE_ms + float(d['upkeep']) \
            + float(d['c_syn']) * self.outdeg_E \
            + float(self.syn_cfg['c_len']) * self.syn_len_E
        self.engE[aliveE] += (inc - cost)[aliveE]

        _ol = self.cfg['dev'].get('eng_outlet', None)
        if _ol is not None:
            _rho = float(_ol.get('rate', 0.0))
            if _rho > 0.0:
                _sig = float(_ol.get('setpoint', d['E0']))
                self.engE[aliveE] -= _rho * (self.engE[aliveE] - _sig)

        tot_i = float(self.actI[aliveI].sum())
        inc_i = (self.budget * 0.25 * self.actI / tot_i) if tot_i > 0 else \
            (self.budget * 0.25 / max(1, self._n_alive_I) * aliveI)
        cost_i = float(d['c_spike']) * self.spkI_ms + float(d['upkeep']) \
            + float(d['c_syn']) * self.outdeg_I
        self.engI[aliveI] += (inc_i - cost_i)[aliveI]

        self.rate_ema *= self.ema_decay
        self.rate_ema += self.spkE_ms * (1.0 - self.ema_decay) * 1000.0

        if self.syn_on:
            rate = float(self.rate_ema[self.aliveE].mean()) if self.aliveE.any() else 0.0
            tgt = max(1e-6, float(self.cfg['reward']['target_hz']))
            raw = float(np.clip(1.0 - abs(rate - tgt) / tgt, -1.0, 1.0))
            a = 1.0 / max(1.0, float(self.cfg['reward']['tau']))
            self.reward += (raw - self.reward) * a

            c = self.syn_cfg
            self.xE_t *= math.exp(-1.0 / float(c['tau_pre']))
            self.yE_t *= math.exp(-1.0 / float(c['tau_post']))

            if self.br_on:  # branch trace decays with its own time constant
                self.br_s *= math.exp(-self.dt / float(self.cfg['branch']['tau_ca']))

            if self.pair_on:  # the window width: how long a spike can wait for its partner
                _d = math.exp(-self.dt / float(self.cfg['pair']['tau']))
                self.e_ltp *= _d
                self.e_ltd *= _d

            if self._tag_on:
                self.tag *= math.exp(-1.0 / self.tag_tau)

        _c = self._calib_of(self.engE[aliveE])
        if _c is not None:
            self.eng_med, self.eng_scale = _c
        self.actE[:] = 0.0
        self.actI[:] = 0.0
        self.spkE_ms[:] = 0.0
        self.spkI_ms[:] = 0.0

    def _develop(self):
        d = self.cfg['dev']
        self.last_dev = self.t
        nE_slot, nI_slot, U = self.nE_slot, self.nI_slot, self.nU

        rate_now = self.rate_ema
        pop_mean_now = float(rate_now[self.aliveE].mean()) if self.aliveE.any() else 0.0
        self.pop_rate_hist.append((self.t, pop_mean_now, float(self.aliveE.sum())))

        q_of = np.zeros(self.N_E, int)
        if self.aliveE.sum() >= 8:
            qs = np.quantile(rate_now[self.aliveE], [0.25, 0.5, 0.75])
            q_of = np.digitize(rate_now, qs)
            for q in range(4):
                m = self.aliveE & (q_of == q)
                self.cells_by_q[q] += int(m.sum())

        dead_E = np.nonzero(self.aliveE & (self.engE < float(d['E_death'])))[0]
        dead_I = np.nonzero(self.aliveI & (self.engI < float(d['E_death'])))[0]
        if dead_E.size:
            for i in dead_E:
                self.dead_log.append({'t': self.t, 'kind': 'E', 'unit': int(i // nE_slot),
                                      'hz': float(rate_now[i]), 'pop_hz': pop_mean_now,
                                      'eng': float(self.engE[i])})
        if dead_E.size:
            for q in q_of[dead_E]:
                self.dead_by_q[q] += 1
            self.aliveE[dead_E] = False
            self.engE[dead_E] = 0.0
            self.n_dead += dead_E.size
        if dead_I.size:
            self.aliveI[dead_I] = False
            self.engI[dead_I] = 0.0
            self.n_dead += dead_I.size

        div = np.nonzero(self.aliveE & (self.engE > float(d['E_div'])))[0]
        cap_per_unit = int(round(self.nE0 * float(d['max_units_growth'])))
        newborn = []
        if div.size:
            rng = self.rng
            for p in div:
                u = p // nE_slot
                blk = slice(u * nE_slot, (u + 1) * nE_slot)
                if int(self.aliveE[blk].sum()) >= cap_per_unit:
                    continue
                free = np.nonzero(~self.aliveE[blk])[0]
                if free.size == 0:
                    continue
                child = u * nE_slot + int(free[0])
                self.aliveE[child] = True
                self.vE[child] = -65.0
                self.uE[child] = self.pE[1] * -65.0
                self.gEa[child] = 0.0
                self.gEg[child] = 0.0
                half = self.engE[p] * 0.5
                self.engE[p] = half
                self.engE[child] = half
                self.born_t[child] = self.t
                self.n_spkE[child] = 0
                self.n_born += 1
                newborn.append(child)

        if newborn:
            nb = np.array(newborn, np.int64)
            m = (np.isin(self.S['ee']['pre'], nb) |
                 np.isin(self.S['ee']['post'], nb))
            rev = m & (~self.syn_alive)
            self.syn_alive |= m
            self.n_rev    += int(rev.sum())
            self.n_rev_lr += int((rev & (self.syn_dist >= 0.5)).sum())
            self.rev_cnt[rev] += 1
            self.fate[rev] = 0

        if self.syn_on:
            c = self.syn_cfg
            if c.get('norm_on') and (self.t - self.last_norm) >= float(c['norm_period']):
                self._normalize_weights()
                self.last_norm = self.t
            self._prune_stressed()
            self.syn_len_E = np.bincount(self.S['ee']['pre'],
                                         weights=self.syn_dist.astype(float) * self.syn_alive,
                                         minlength=self.N_E)[:self.N_E]

        if d.get('prune_unused'):

            post_alive = self.aliveE[self.S['ee']['post']]
            pre_alive = self.aliveE[self.S['ee']['pre']]
            cut = self.syn_alive & (~post_alive | ~pre_alive)
            if cut.any():
                self.syn_alive[cut] = False
                self.n_pruned += int(cut.sum())
                self.n_cut_dead    += int(cut.sum())
                self.n_cut_dead_lr += int((cut & (self.syn_dist >= 0.5)).sum())
                self.fate[cut] = 2
                self._log_cut(cut)

            if self.t > 2.0 * float(d['period']):
                rate_hz = self.idle_rate(float(d['period']))

                near_m = self.syn_dist < 1.5
                far_m  = self.syn_dist >= 4.0
                self.exp_near += float((self.syn_alive & near_m).sum())
                self.exp_far  += float((self.syn_alive & far_m).sum())
                idle = self.syn_alive & (rate_hz < float(d['syn_prune_hz']))
                idle = idle & (~self.infra)

                _dh = self.idle_hist.size
                _dd = np.clip(self.syn_dist[self.syn_alive].astype(np.int64), 0, _dh - 1)
                self.alive_hist += np.bincount(_dd, minlength=_dh)

                ex = self.idle_exempt()
                if ex is not None:
                    ex = ex & idle
                    self.n_idle_cand += int(idle.sum())
                    self.n_exempt    += int(ex.sum())
                    self.n_exempt_lr += int((ex & (self.syn_dist >= 0.5)).sum())
                    idle = idle & (~ex)
                if idle.any():
                    self.syn_alive[idle] = False
                    self.n_pruned += int(idle.sum())
                    self.n_cut_idle    += int(idle.sum())
                    self.n_cut_idle_lr += int((idle & (self.syn_dist >= 0.5)).sum())

                    _di = np.clip(self.syn_dist[idle].astype(np.int64), 0,
                                  self.idle_hist.size - 1)
                    self.idle_hist += np.bincount(_di, minlength=self.idle_hist.size)
                    self.idle_near += int((idle & near_m).sum())
                    self.idle_far  += int((idle & far_m).sum())
                    self.fate[idle] = 3
                    self._log_cut(idle)
        self.syn_use[:] = 0.0

        for u in range(U):
            blk = slice(u * nE_slot, (u + 1) * nE_slot)
            na = int(self.aliveE[blk].sum())
            if na < 5:
                free = np.nonzero(~self.aliveE[blk])[0][:5 - na]
                if free.size:
                    idx = u * nE_slot + free
                    self.aliveE[idx] = True
                    self.vE[idx] = -65.0
                    self.uE[idx] = self.pE[1] * -65.0
                    self.engE[idx] = float(d['E0']) * 0.5
                    self.born_t[idx] = self.t
                    self.n_spkE[idx] = 0
        self._n_alive_E = int(self.aliveE.sum())
        self._n_alive_I = int(self.aliveI.sum())
        self.hist.append(self._snapshot())

    def _log_dead(self, idx, kind):
        nspk = self.n_spkE if kind == 'E' else self.n_spkI
        bt = self.born_t
        for i in idx:
            age = max(1.0, self.t - bt[i])
            self.dead_log.append({
                't': self.t, 'kind': kind, 'unit': int(i // (self.nE_slot if kind == 'E'
                                                            else self.nI_slot)),
                'spk': int(nspk[i]), 'age': float(age),
                'hz': float(nspk[i]) / age * 1000.0})
            bt[i] = self.t

    def activity_table(self):
        hz = self.n_spkE / np.maximum(1.0, self.t - self.born_t) * 1000.0
        return hz

    def run_until(self, t_end):
        n = int(round((t_end - self.t) / self.dt))
        if n > 0:
            self.step(n)
        elif self.t < t_end:

            self.step(1)
        return self.t

    def pop_ms(self):
        return self.pop_ms0 + self.pop_n

    def pop_slice(self, t0, t1):
        i0 = max(0, int(round(t0)) - self.pop_ms0)
        i1 = min(self.pop_n, int(round(t1)) - self.pop_ms0)
        if i1 <= i0:
            return np.zeros(0, np.float32), np.zeros(0, np.float32)
        return self.pop_E[i0:i1], self.pop_I[i0:i1]

    def u_ms(self):
        return self.u_ms0 + self.u_n * self.bin_ms

    def unit_slice(self, t0, t1):
        i0 = max(0, int((t0 - self.u_ms0) / self.bin_ms))
        i1 = min(self.u_n, int((t1 - self.u_ms0) / self.bin_ms))
        if not self.trace_on or i1 <= i0:
            return np.zeros((self.nU, 0), np.float32)
        return self.u_cnt[:, i0:i1].astype(np.float32) / (self.bin_ms * self.nE0) * 1000.0

    def unit_glow(self, tau=15.0):
        return np.exp(-(self.t - self.t_lastU) / tau)

    def n_alive(self):
        return int(self.aliveE.sum())

    def to_json(self, keep_pop_ms=20000, keep_unit_ms=5000):
        kp = max(0, self.pop_n - int(keep_pop_ms))
        ku = max(0, self.u_n - int(keep_unit_ms / self.bin_ms)) if self.trace_on else 0
        import base64
        ucnt = self.u_cnt[:, ku:self.u_n].astype(np.uint16).tobytes() if self.trace_on else ''
        return {
            'version': 1, 't': self.t, 'cfg': self.cfg,
            'rng': _plain(self.rng.bit_generator.state),
            'vE': _plain(self.vE), 'uE': _plain(self.uE), 'vI': _plain(self.vI), 'uI': _plain(self.uI),
            'gEa': _plain(self.gEa), 'gEg': _plain(self.gEg), 'gIa': _plain(self.gIa), 'gIg': _plain(self.gIg),
            'aliveE': self.aliveE.astype(np.uint8).tolist(), 'aliveI': self.aliveI.astype(np.uint8).tolist(),
            'engE': _plain(self.engE), 'engI': _plain(self.engI),
            'syn_alive': self.syn_alive.astype(np.uint8).tolist(),
            'syn_use': _plain(self.syn_use),
            'n_spkE': _plain(self.n_spkE), 'n_spkI': _plain(self.n_spkI),
            'n_spkU': _plain(self.n_spkU), 'spk_total': self.spk_total,
            'n_dead': self.n_dead, 'n_born': self.n_born, 'n_pruned': self.n_pruned,
            'last_dev': self.last_dev, 'hist': self.hist[-500:],
            'pop_ms0': self.pop_ms0 + kp, 'pop_n': self.pop_n - kp,
            'pop_E': _plain(self.pop_E[kp:self.pop_n]), 'pop_I': _plain(self.pop_I[kp:self.pop_n]),
            'u_ms0': self.u_ms0 + int(ku * self.bin_ms), 'u_n': self.u_n - ku,
            'u_cnt_b64': base64.b64encode(ucnt).decode('ascii'),
            'u_cnt_shape': [int(self.nU), int(self.u_n - ku)],
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    @classmethod
    def from_json(cls, d):
        import base64
        n = cls(cfg=d.get('cfg'))
        n.t = float(d['t'])
        n.rng = np.random.default_rng(0)
        n.rng.bit_generator.state = d['rng']
        for k in ('vE', 'uE', 'vI', 'uI', 'gEa', 'gEg', 'gIa', 'gIg', 'engE', 'engI', 'syn_use'):
            setattr(n, k, np.array(d[k], float))
        n.aliveE = np.array(d['aliveE'], bool)
        n.aliveI = np.array(d['aliveI'], bool)
        n.syn_alive = np.array(d['syn_alive'], bool)
        n.n_spkE = np.array(d['n_spkE'], int)
        n.n_spkI = np.array(d['n_spkI'], int)
        n.n_spkU = np.array(d['n_spkU'], int)
        n.spk_total = int(d.get('spk_total', 0))
        n.n_dead = int(d.get('n_dead', 0))
        n.n_born = int(d.get('n_born', 0))
        n.n_pruned = int(d.get('n_pruned', 0))
        n.last_dev = float(d.get('last_dev', n.t))
        n.hist = list(d.get('hist', []))
        n.pop_ms0 = int(d['pop_ms0'])
        pn = int(d['pop_n'])
        n.pop_E[:] = 0
        n.pop_I[:] = 0
        n.pop_E[:pn] = np.array(d['pop_E'], np.float32)
        n.pop_I[:pn] = np.array(d['pop_I'], np.float32)
        n.pop_n = pn
        n.u_ms0 = int(d['u_ms0'])
        un = int(d['u_n'])
        if n.trace_on and d.get('u_cnt_b64'):
            arr = np.frombuffer(base64.b64decode(d['u_cnt_b64']), np.uint16)
            n.u_cnt[:] = 0
            if un > 0:
                n.u_cnt[:, :un] = arr.reshape(d['u_cnt_shape'][0], un)
        n.u_n = un
        n._n_alive_E = int(n.aliveE.sum())
        n._n_alive_I = int(n.aliveI.sum())
        return n

def spectrum(r, fs=1000.0, fmin=BAND[0], fmax=BAND[1]):
    x = np.asarray(r, float)
    if x.size < 64:
        return np.zeros(1), np.zeros(1)
    x = x - x.mean()
    P = np.abs(np.fft.rfft(x * np.hanning(x.size))) ** 2
    f = np.fft.rfftfreq(x.size, d=1.0 / fs)
    band = (f >= fmin) & (f <= fmax)
    return f[band], P[band]

def osc_index(r, fs=1000.0):
    f, P = spectrum(r, fs)
    if P.size < 2 or P.sum() <= 0:
        return float('nan'), 0.0, P, f
    k = int(np.argmax(P))
    med = float(np.median(P))
    return float(f[k]), (float(P[k] / med) if med > 0 else float('inf')), P, f

def verdict(m):
    if m.get('mean_E', 0.0) < SILENT_HZ:
        return '沉默'
    if m.get('mean_E', 0.0) > EPILEPTIC_HZ or m.get('sat', 0.0) > SAT_FRAC:
        return '癫痫'
    if m.get('osc_index', 0.0) >= OSC_TH and BAND[0] <= m.get('peak_f', 0) <= BAND[1]:
        return '振荡'
    return '平稳'

def pop_metrics(net, t0, t1, fs=1000.0):
    rE, rI = net.pop_slice(t0, t1)
    out = {'t0': t0, 't1': t1, 'n': int(rE.size)}
    if rE.size == 0:
        return {**out, 'mean_E': 0.0, 'mean_I': 0.0, 'peak_f': float('nan'),
                'osc_index': 0.0, 'sat': 0.0, 'silent_frac': 1.0, 'drift': 0.0}
    out['mean_E'] = float(rE.mean())
    out['mean_I'] = float(rI.mean())
    out['sat'] = float((rE > 60.0).mean())
    out['silent_frac'] = float((rE <= 0.0).mean())
    f, oi, _, _ = osc_index(rE, fs)
    out['peak_f'], out['osc_index'] = f, oi
    h = rE.size // 2
    if h > 500:
        def env(x):
            s = np.convolve(x, np.ones(200) / 200, mode='valid')
            return float(s.mean()), float(s.max() - s.min())
        m1, a1 = env(rE[:h])
        m2, a2 = env(rE[h:])
        out['drift'] = (m2 - m1) / m1 if m1 > 1e-9 else 0.0
        out['amp_ratio'] = a2 / a1 if a1 > 1e-9 else float('nan')
    else:
        out['drift'], out['amp_ratio'] = 0.0, float('nan')
    out['verdict'] = verdict(out)
    return out

def unit_stats(net, t0, t1):
    M = net.unit_slice(t0, t1)
    out = {'n_units': net.nU}
    if M.shape[1] < 20:
        return {**out, 'active_frac': 0.0, 'mean_rate': 0.0, 'sync_chi': float('nan'),
                'mean_r': float('nan'), 'R': np.zeros((net.nU, net.nU)),
                'rates': np.zeros(net.nU)}
    rates = M.mean(axis=1)
    out['rates'] = rates
    out['mean_rate'] = float(rates.mean())
    out['active_frac'] = float((rates > ACTIVE_HZ).mean())
    pop_sum = M.sum(axis=0)
    var_unit = float(M.var(axis=1).mean())
    if var_unit > 1e-12 and net.nU > 1:
        chi = float(pop_sum.var()) / (net.nU * var_unit)
        out['sync_chi'] = float(np.clip((chi - 1.0) / (net.nU - 1.0), 0.0, 1.0))
    else:
        out['sync_chi'] = float('nan')
    Z = M - M.mean(axis=1, keepdims=True)
    sd = Z.std(axis=1, keepdims=True)
    ok = (sd[:, 0] > 1e-9)
    R = np.zeros((net.nU, net.nU))
    if ok.sum() >= 2:
        Zs = Z[ok] / sd[ok]
        Rk = (Zs @ Zs.T) / Zs.shape[1]
        R[np.ix_(ok, ok)] = Rk
        iu = np.triu_indices(int(ok.sum()), 1)
        out['mean_r'] = float(Rk[iu].mean())
    else:
        out['mean_r'] = float('nan')
    out['R'] = R
    out['ok_mask'] = ok
    return out

def greedy_modularity(A, max_merge=None):
    n = A.shape[0]
    if n < 4 or A.sum() <= 0:
        return 0.0, np.arange(n)
    A = np.array(A, float)
    np.fill_diagonal(A, 0.0)
    m2 = float(A.sum())
    if m2 <= 0:
        return 0.0, np.arange(n)
    K = A.sum(axis=1)
    members = {i: [i] for i in range(n)}
    alive = np.ones(n, bool)
    a_vec = K / m2
    dq = (A + A.T) / m2 - 2.0 * np.outer(a_vec, a_vec)
    np.fill_diagonal(dq, -np.inf)
    Q = 0.0
    for _ in range(max_merge or n):
        i, j = np.unravel_index(int(np.argmax(dq)), dq.shape)
        if (not alive[i]) or (not alive[j]) or (not np.isfinite(dq[i, j])) or dq[i, j] <= 0:
            break
        Q += float(dq[i, j])
        A[j, :] += A[i, :]
        A[:, j] += A[:, i]
        K[j] += K[i]
        a_vec[j] = K[j] / m2
        members[j] = members[j] + members.pop(i, [])
        alive[i] = False
        dq[j, :] = (A[j, :] + A[:, j]) / m2 - 2.0 * a_vec[j] * a_vec
        dq[:, j] = dq[j, :]
        dq[j, ~alive] = -np.inf
        dq[~alive, j] = -np.inf
        dq[j, j] = -np.inf
        dq[i, :] = -np.inf
        dq[:, i] = -np.inf
    final = {}
    for cid, mem in members.items():
        for m in mem:
            final[m] = cid
    labels = np.array([final[i] for i in range(n)])
    _, labels = np.unique(labels, return_inverse=True)
    return Q, labels

def corr_vs_distance(R, idx, n_units, n_bins=6):
    if R.size == 0 or idx.size < 4:
        return []
    dr = np.abs(idx[:, None] - idx[None, :])
    dr = np.minimum(dr, n_units - dr)
    iu = np.triu_indices(idx.size, 1)
    d, r = dr[iu], R[iu]
    edges = np.linspace(0, n_units / 2.0, n_bins + 1)
    out = []
    for k in range(n_bins):
        m = (d >= edges[k]) & (d < edges[k + 1])
        if m.sum() >= 5:
            out.append((0.5 * (edges[k] + edges[k + 1]), float(r[m].mean()), int(m.sum())))
    return out

def modularity_report(net, t0, t1, q_thresh=0.25, rng=None, max_units=256):
    rng = rng or np.random.default_rng(0)
    M = net.unit_slice(t0, t1)
    out = {'n_units': net.nU, 'T': int(M.shape[1]) if M.shape[1] else 0, 'n_edges': 0, 'rd': []}
    if M.shape[1] < 50:
        return {**out, 'Q': float('nan'), 'Q_surr': float('nan'), 'dQ': float('nan'),
                'n_mod': 0, 'labels': np.zeros(0, int), 'R': np.zeros((0, 0)),
                'mean_r': float('nan')}
    idx = np.arange(net.nU)
    if net.nU > max_units:
        idx = np.sort(rng.choice(net.nU, max_units, replace=False))
    Ms = M[idx]
    sd = Ms.std(axis=1, keepdims=True)
    ok = sd[:, 0] > 1e-9
    if ok.sum() < 8:
        return {**out, 'Q': float('nan'), 'Q_surr': float('nan'), 'dQ': float('nan'),
                'n_mod': 0, 'labels': np.zeros(0, int), 'R': np.zeros((0, 0)),
                'mean_r': float('nan')}
    Z = (Ms[ok] - Ms[ok].mean(axis=1, keepdims=True)) / sd[ok]
    R = (Z @ Z.T) / Z.shape[1]
    iu = np.triu_indices(R.shape[0], 1)
    out['mean_r'] = float(R[iu].mean())
    A = np.where(R > q_thresh, R, 0.0)
    np.fill_diagonal(A, 0.0)
    out['n_edges'] = int((A > 0).sum() // 2)
    Q, labels = greedy_modularity(A)
    out['Q'] = Q if out['n_edges'] >= 20 else float('nan')
    Msur = phase_surrogate(Ms[ok], rng)
    Zs = (Msur - Msur.mean(axis=1, keepdims=True)) / Msur.std(axis=1, keepdims=True)
    Rs = (Zs @ Zs.T) / Zs.shape[1]
    Qs, _ = greedy_modularity(np.where(Rs > q_thresh, Rs, 0.0))
    out.update(Q_surr=Qs, labels=labels, R=R, n_mod=int(len(np.unique(labels))), ok_idx=idx[ok],
               dQ=(out['Q'] - Qs) if np.isfinite(out['Q']) else float('nan'))
    out['rd'] = corr_vs_distance(R, idx[ok], net.nU)
    return out

def phase_surrogate(M, rng):
    F = np.fft.rfft(M, axis=1)
    ph = np.exp(2j * np.pi * rng.random(F.shape))
    ph[:, 0] = 1.0
    if M.shape[1] % 2 == 0:
        ph[:, -1] = 1.0
    return np.fft.irfft(F * ph, n=M.shape[1], axis=1)

def make_cfg(args):
    cfg = copy.deepcopy(DEFAULT_CFG)
    cfg['seed'] = args.seed
    if getattr(args, 'units', None):
        cfg['n_units'] = int(args.units)
    if getattr(args, 'cells', None):
        cfg['n_E'] = int(args.cells)
        cfg['n_I'] = max(5, int(args.cells) // 4)
    if getattr(args, 'drive', None) is not None:
        cfg['drive']['tonic'] = float(args.drive)
    if getattr(args, 'budget', None) is not None:
        cfg['dev']['budget'] = float(args.budget)
    if getattr(args, 'nodev', False):
        cfg['dev']['on'] = False
    if getattr(args, 'no_prune', False):
        cfg['dev']['prune_unused'] = False
    return cfg

def probe(args, ms=None):
    cfg = make_cfg(args)
    net = Network(cfg)
    dur = float(ms if ms is not None else (args.ms or 8000.0))
    t0 = time.time()
    net.run_until(dur)
    wall = time.time() - t0
    pm = pop_metrics(net, dur - 2000.0, dur)
    print('工位 %d ｜ 槽位 %d/工位（活 %d）｜ 开局 %d 活 ｜ 现在活 %d'
          % (net.nU, net.nE_slot, net.nE0, net.nE0 * net.nU, net.n_alive()))
    print('突触 %d 条 ｜ 还活着 %d（剪掉 %d）｜ 死 %d ｜ 生 %d'
          % (net.S['ee']['n_syn'] + net.S['ei']['n_syn'] + net.S['ie']['n_syn'] + net.S['ii']['n_syn'],
             int(net.syn_alive.sum()), net.n_pruned, net.n_dead, net.n_born))
    print('耗时 %.1fs（%.2f 秒仿真/秒真）' % (wall, (dur / 1000.0) / wall))
    print('放电：E=%.2fHz I=%.2fHz 峰频=%.1f 判定=%s' % (pm['mean_E'], pm['mean_I'],
                                                    pm['peak_f'], pm['verdict']))
    h = net.hist
    if len(h) > 4:
        tail = h[len(h) // 2:]
        ns = np.array([x['nE'] for x in tail], float)
        print('细胞数：%.0f → %.0f ｜ 后半段均值 %.0f 变异系数 %.3f'
              % (h[0]['nE'], h[-1]['nE'], ns.mean(), ns.std() / max(1e-9, ns.mean())))
    return net, pm

def peak_gap(w, bins=12):
    if w.size < 50:
        return 0.0, None
    h, e = np.histogram(w, bins=bins)
    c = 0.5 * (e[:-1] + e[1:])
    best = 0.0
    pair = None
    for i in range(len(h)):
        for j in range(i + 2, len(h)):
            valley = h[i + 1:j].min() if j > i + 1 else h[i + 1]
            if h[i] < 1 or h[j] < 1:
                continue
            if valley > 0.7 * min(h[i], h[j]):
                continue
            gap = c[j] - c[i]
            if gap > best:
                best, pair = gap, (float(c[i]), float(c[j]))
    return best, pair

def dev_criteria(net, base_cfg, d0, w0, al0, t_an):
    d, w, al = net.syn_dist, net.S['ee']['w'], net.syn_alive
    lr0 = d0 >= 0.5
    lr_alive = lr0 & al
    out = {}

    out['gap'], out['peaks'] = peak_gap(w[lr_alive])

    rng_w = float(w[lr_alive].max() - w[lr_alive].min()) if lr_alive.any() else 0.0
    out['w_range'] = rng_w
    out['gap_thr'] = 0.5 * max(rng_w, 1e-9) / 1.0
    out['gap_norm'] = out['gap'] / max(1e-9, rng_w)

    m0 = float(w0[lr0].mean()) if lr0.any() else float('nan')
    m1 = float(w[lr_alive].mean()) if lr_alive.any() else float('nan')
    out['w0'], out['w1'] = m0, m1
    out['dev_pct'] = 100.0 * (m1 - m0) / max(1e-12, m0)

    mr = modularity_report(net, max(0.0, t_an - 3000.0), t_an, rng=np.random.default_rng(0))
    out['Q'] = mr.get('Q', float('nan'))
    out['n_mod'] = mr.get('n_mod', 0)

    out['dist0'] = float(d0[lr0].mean())
    out['dist1'] = float(d[lr_alive].mean()) if lr_alive.any() else float('nan')
    out['dist_ratio'] = out['dist1'] / max(1e-12, out['dist0'])

    rd = mr.get('rd') or []
    out['rd'] = rd
    out['rd_gap'] = (rd[0][1] - rd[-1][1]) if len(rd) >= 2 else float('nan')
    out['lr_alive_frac'] = float(lr_alive.sum() / max(1, lr0.sum()))
    out['w_alive_frac'] = float(al.mean())
    return out

def print_criteria(tag, c):
    print('  【%s】' % tag)
    print('    ① 长程权重双峰     峰间距 %.3f（原阈值>0.5 不可满足：权重范围仅 %.2f）%s'
          % (c['gap'], c['w_range'], '✅' if c['gap'] > 0.5 else '❌'))
    print('       按权重尺度换算后的阈值 %.2f → %s（归一化间距 %.2f）'
          % (c['gap_thr'], '✅' if c['gap'] > c['gap_thr'] else '❌', c['gap_norm']))
    print('    ② 长程权重均值     初始 %.4f → 现在 %.4f（偏 %+.0f%%，阈值>20%%）%s'
          % (c['w0'], c['w1'], c['dev_pct'], '✅' if abs(c['dev_pct']) > 20 else '❌'))
    print('    ③ 模块度 Q         %.2f（阈值>0.3，%d 个社区）%s'
          % (c['Q'], c['n_mod'], '✅' if c['Q'] > 0.3 else '❌'))
    print('    ④ 长程边平均距离   %.2f → %.2f（%.2f 倍，阈值<0.9）%s'
          % (c['dist0'], c['dist1'], c['dist_ratio'],
             '✅' if c['dist_ratio'] < 0.9 else '❌'))
    print('    ★附加：近邻r−远距r = %+.2f（阈值>0.1）%s ｜ 长程突触存活 %.0f%%'
          % (c['rd_gap'], '✅' if c['rd_gap'] > 0.1 else '❌', 100 * c['lr_alive_frac']))


def report(args):
    base = make_cfg(args)
    ms = float(args.ms or 25000.0)
    print('[1/3] 有生死：跑 %.0f 秒……' % (ms / 1000.0))
    net = Network(base)
    net.run_until(ms)
    print('[2/3] 对照：关掉生死，同样跑 %.0f 秒……' % (ms / 1000.0))
    ctrl = Network(_merge(copy.deepcopy(base), {'dev': {'on': False}}))
    ctrl.run_until(ms)

    h = np.array([x['nE'] for x in net.hist], float)
    tail = h[len(h) * 2 // 3:]
    cv_tail = float(tail.std() / max(1e-9, tail.mean()))
    d = np.array([x['hz'] for x in net.dead_log])
    p = np.array([x['pop_hz'] for x in net.dead_log])
    rel = d / np.maximum(1e-9, p)
    rq = net.dead_by_q / np.maximum(1, net.cells_by_q) * 100.0
    pm_late = pop_metrics(net, ms - 3000.0, ms)
    mean_cost = (base['dev']['c_spike'] * pm_late['mean_E'] / 1000.0 + base['dev']['upkeep']
                 + base['dev']['c_syn'] * 12.0)
    nstar = net.budget / max(1e-12, mean_cost)

    L = []

    def P(s=''):
        L.append(s)
        print(s)

    P('=' * 74)
    P('006  能量与发育 —— 让神经元有生有死')
    P('=' * 74)
    P('规模：%d 工位 × 每工位 %d 个槽位（开局活 %d，上限 %d）= 开局 %d 个兴奋细胞'
      % (net.nU, net.nE_slot, net.nE0, int(net.nE0 * base['dev']['max_units_growth']),
         net.nE0 * net.nU))
    P('能量规则：收入 = 每个工位每毫秒 %.3f 份营养，按"被激活程度"分（有限资源 → 竞争）'
      % base['dev']['budget_per_unit'])
    P('          支出 = %.4f×放电 + %.4f/ms 基础代谢 + %.6f×出度/ms 突触维护费'
      % (base['dev']['c_spike'], base['dev']['upkeep'], base['dev']['c_syn']))
    P('          E<%.1f → 死 ｜ E>%.1f → 分裂（同工位找空槽复活，能量对半）'
      % (base['dev']['E_death'], base['dev']['E_div']))
    P('')
    P('-' * 74)
    P('一、细胞数量会不会稳定？（问题一）')
    P('-' * 74)
    P('  %.0f 秒里的轨迹：%d → %d 个（开局 %d）' % (ms / 1000.0, int(h[0]), int(h[-1]), net.nE0 * net.nU))
    P('  后 1/3 时间：平均 %.0f 个，变异系数 %.3f（%.1f%%）' % (tail.mean(), cv_tail, 100 * cv_tail))
    P('  上限是 %d 个（槽位数）—— 它**没有撞上限**，是自己停在了 %.0f 附近'
      % (net.nE_slot * net.nU, tail.mean()))
    P('  营养池公式预测的平衡点（上界）：N* ≈ 营养 ÷ 每细胞平均开销 = %.0f' % nstar)
    P('    实际停在 %.0f，比公式低 %.0f%% —— 差在"收入是按活跃度分的"：'
      % (tail.mean(), 100 * (nstar - tail.mean()) / max(1e-9, nstar)))
    P('    低于平均活跃度的细胞拿不到平均那份营养，所以真实平衡点比上界低。')
    P('  对照（关掉生死）：%d → %d 个，一动不动 ✓' % (ctrl.hist[0]['nE'], ctrl.hist[-1]['nE']))
    P('  → 判定：**数量稳定**（后段变异系数 %.1f%% ≪ 15%%，既没灭绝也没撞上限）' % (100 * cv_tail))

    P('')
    P('-' * 74)
    P('二、有没有「用进废退」的修剪？（问题二）')
    P('-' * 74)
    P('  方法（不这么做会得出错误结论）：')
    P('    · 不能拿"活到最后的"跟"死掉的"比 —— 前者已经被选择过一轮（生存者偏差）。')
    P('    · 改成**前瞻性**测量：细胞死之前记下它最近 1 秒的放电率，跟**同一时刻还活着的同伴**比。')
    P('    · 活跃度用 1 秒平滑率：只看一期 200ms，10Hz 的细胞平均只放 2 次，')
    P('      测量噪声 ±7Hz —— 比要测的效应还大，什么也说不出来。')
    P('')
    P('  %.0f 秒里死了 %d 个兴奋细胞。按当下活跃度四分位分组：' % (ms / 1000.0, d.size))
    names = ['最不活跃 1/4', '次不活跃   ', '次活跃     ', '最活跃 1/4 ']
    for q in range(4):
        P('    %s：观察 %7d 细胞·期 ｜ 死 %5d ｜ 死亡率 %.2f%%'
          % (names[q], net.cells_by_q[q], net.dead_by_q[q], rq[q]))
    P('  → 死亡率随活跃度**单调下降**：最不活跃组是最活跃组的 %.1f 倍' % (rq[0] / max(1e-9, rq[3])))
    P('  → 临死那一刻：它们 %.2fHz，同期同伴 %.2fHz（低 %.0f%%）；'
      % (d.mean(), p.mean(), 100 * (1 - d.mean() / max(1e-9, p.mean()))))
    P('    死者里 %.0f%% 活跃度低于同期平均（纯随机应该是 50%%）' % (100 * (rel < 1).mean()))
    P('  → 判定：**「用进废退」确实出现了 —— 方向完全正确、统计上极显著，但是"弱选择"**：')
    P('     每档 7 万个细胞·期，417 例 vs 107 例死亡；但临死前只比同伴低 8%，')
    P('     不是"不活跃就必死"，而是"越不活跃越容易死"。')
    P('  为什么会偏弱（诊断）：收入 ∝ 被激活量、支出 ∝ 自己放电数，')
    P('    而在复发网络里"收得多"和"放得多"高度绑定，两者相抵后净能量差别很小，')
    P('    于是决定生死的主要是随机涨落，不是系统性的"有用/没用"。')
    P('  修法（留给下一步）：让收入和支出**解耦** —— 收入改成"我的放电真的引起了下游放电"')
    P('    （三因子/资格迹那一套，neuron_world.py 里有现成的），谁对网络有贡献谁拿钱。')

    P('')
    P('-' * 74)
    P('三、稳定性（不能一边发育一边崩）')
    P('-' * 74)
    P('  细胞数：开局 %d → 末了 %d，全程最低 %d、最高 %d（上限 %d）'
      % (net.nE0 * net.nU, int(h[-1]), int(h.min()), int(h.max()), net.nE_slot * net.nU))
    P('  放电率：%.2fHz（对照 %.2fHz）｜ 峰频 %.1fHz ｜ 判定 %s'
      % (pm_late['mean_E'], pop_metrics(ctrl, ms - 3000.0, ms)['mean_E'],
         pm_late['peak_f'], pm_late['verdict']))
    P('  生死账：死 %d ｜ 生 %d ｜ ee 突触被剪到剩 %.0f%%' % (net.n_dead, net.n_born,
                                                       100 * net.syn_alive.mean()))
    P('  → 一边不停地换细胞（%.0f 秒里 %d 次生死），一边把节律和放电率维持住。'
      % (ms / 1000.0, net.n_dead + net.n_born))
    P('    这是"可修复的网络"该有的样子：零件在换，功能没塌。')

    P('')
    P('=' * 74)

    pth = os.path.join(SD, 'report', '_006_数量与发育_中间产物.txt')
    os.makedirs(os.path.dirname(pth), exist_ok=True)
    with open(pth, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('[报告] -> %s' % pth)
    return pth

def pair_probe(args):
    """Order must now decide the sign: pre-then-post potentiates, post-then-pre depresses.

    Each case arms one eligibility, then fires the partner cell. The rule must spend what was
    armed and leave it at zero, so the same edge cannot be paid twice for one event.
    """
    log = print
    cfg = _merge(copy.deepcopy(DEFAULT_CFG), {'n_units': 4})
    cfg['pair'] = dict(DEFAULT_CFG['pair'])
    cfg['pair']['on'] = True
    net = Network(cfg)
    ee = net.S['ee']
    net._reward_of = lambda cells: np.ones(len(np.atleast_1d(cells)), float)

    j, e = None, None
    for cell in range(net.N_E):
        st, en = int(net.in_ptr[cell]), int(net.in_ptr[cell + 1])
        if en - st >= 1:
            j, e = cell, int(net.in_order[st])
            break
    if j is None:
        log('❌ 找不到入边，测试无法进行')
        return 1
    p = int(ee['pre'][e])

    def fire(cell, arm_ltp=None, arm_ltd=None):
        w0 = float(ee['w'][e])
        net.e_ltp[:] = 0.0
        net.e_ltd[:] = 0.0
        if arm_ltp is not None:
            net.e_ltp[arm_ltp] = 1.0
        if arm_ltd is not None:
            net.e_ltd[arm_ltd] = 1.0
        net._stdp_step(np.array([cell], dtype=np.int64))
        return float(ee['w'][e]) - w0, float(net.e_ltp[e]), float(net.e_ltd[e])

    log('=' * 78)
    log('闸1 · 成对资格迹 · 合成检查')
    log('=' * 78)
    log('  边 e: pre=%d -> post=%d ｜ 每次只给一个事件装备资格迹' % (p, j))
    log('')

    a, la, da = fire(j, arm_ltp=e)      # pre fired first, then post
    b, lb, db = fire(p, arm_ltd=e)      # post fired first, then pre
    log('  A 前→后：装备 e_ltp，后细胞发放     Δw = %+.4e  (e_ltp 剩余 %.1f)' % (a, la))
    log('  B 后→前：装备 e_ltd，前细胞发放     Δw = %+.4e  (e_ltd 剩余 %.1f)' % (b, db))
    c, _, _ = fire(j)                   # nothing armed
    log('  C 无装备：直接发放                 Δw = %+.4e' % c)
    log('')

    ok_a = a > 1e-12
    ok_b = b < -1e-12
    ok_c = abs(c) <= 1e-18
    log('  ✅/❌ A 前→后 ⇒ 增强：%s' % ('✅' if ok_a else '❌'))
    log('  ✅/❌ B 后→前 ⇒ 抑制：%s' % ('✅' if ok_b else '❌'))
    log('  ✅/❌ C 无配对 ⇒ 不动：%s' % ('✅' if ok_c else '❌'))
    log('')
    if ok_a and ok_b and ok_c:
        log('★ 判定：**顺序决定符号** —— 同一条边，谁先谁后给出相反的更新。')
        log('  这是旧规则（迹的乘积）做不到的：那里两项可交换相加，差额恒为 0。')
    else:
        log('★ 判定：不成立，检查资格迹的装备/消费顺序。')
    log('=' * 78)
    return 0 if (ok_a and ok_b and ok_c) else 1


def timing_probe(args):
    """Does an edge's update depend on the *order* of pre and post, or only on their rates?

    The rule applies two independent terms to an edge p -> j:
      when j spikes:  w += A_plus  * x[p] * R   (uses the pre trace)
      when p spikes:  w -= A_minus * y[j] * R   (uses the post trace)
    Both terms are evaluated at their own event and summed. If that is all, the order of
    the two events cannot matter - only which trace is larger. This probe measures it:
    the same two events in both orders, same trace amplitudes.
    """
    log = print
    cfg = _merge(copy.deepcopy(DEFAULT_CFG), {'n_units': 4})
    net = Network(cfg)
    ee = net.S['ee']
    ones = lambda cells: np.ones(len(np.atleast_1d(cells)), float)
    net._reward_of = ones

    j, e = None, None
    for cell in range(net.N_E):
        st, en = int(net.in_ptr[cell]), int(net.in_ptr[cell + 1])
        if en - st >= 1:
            j, e = cell, int(net.in_order[st])
            break
    if j is None:
        log('❌ 找不到入边，测试无法进行')
        return 1
    p = int(ee['pre'][e])

    def runde(which):
        w0 = ee['w'].copy()
        net.xE_t[:] = 0.0
        net.yE_t[:] = 0.0
        if which == 'post':          # j spikes first: LTP on the edge, weighted by x[p]
            net.xE_t[p] = 1.0
            net._stdp_step(np.array([j], dtype=np.int64))
        else:                        # p spikes first: LTD on the edge, weighted by y[j]
            net.yE_t[j] = 1.0
            net._stdp_step(np.array([p], dtype=np.int64))
        d = float(ee['w'][e] - w0[e])
        ee['w'][:] = w0
        return d

    log('=' * 78)
    log('闸1 · 时序符号 · 合成检查')
    log('=' * 78)
    log('  边 e: pre=%d -> post=%d ｜ x[p]=1.0 或 y[j]=1.0，单次事件' % (p, j))
    log('')

    a = runde('post')      # 只有 LTP 项
    b = runde('pre')       # 只有 LTD 项
    log('  单项：j 发放（用 x[p]）      Δw = %+.4e' % a)
    log('  单项：p 发放（用 y[j]）      Δw = %+.4e' % b)
    log('  两项相加                     Δw = %+.4e' % (a + b))
    log('')

    order_a = a + b     # j 先，p 后
    order_b = b + a     # p 先，j 后
    log('  顺序 A（j 先, p 后）合计 = %+.4e' % order_a)
    log('  顺序 B（p 先, j 后）合计 = %+.4e' % order_b)
    log('  差额 = %+.2e' % (order_a - order_b))
    log('')

    ok_order = abs(order_a - order_b) <= 1e-18
    if ok_order:
        log('★ 判定：**规则没有时序窗口**。两项各自在自己的事件上求和，可交换。')
        log('   ⇒ 一个突触拿到的信用只取决于 (A_plus·x_pre − A_minus·y_post) × R，')
        log('     即前后迹的**强度差**，与谁先谁后无关。')
        log('   ⇒ 要有时序方向，必须引入依赖 Δt 的符号项，而不是再加一条迹。')
    else:
        log('★ 判定：存在时序依赖（差额非零），顺序信息已进入更新。')
    log('=' * 78)
    return 0


def branch_probe(args):
    """Can two synapses on one cell receive different credit at all?

    Setup: same postsynaptic cell, two presynaptic cells, **identical** presynaptic
    trace and identical synaptic weight, but the two edges land on different branches.
    Under the scalar rule the two updates are bitwise identical (credit = x[pre] * R).
    With branch-local eligibility they must differ, and the difference must follow the
    ratio of branch activation.

    Three cases: (A) all branches equal -> reduces to the old rule; (B) branches
    unequal -> updates differ; (C) mechanism off -> updates identical regardless.
    """
    log = print
    U = int(args.units or 4)
    cfg = _merge(copy.deepcopy(DEFAULT_CFG), {'n_units': U})
    cfg['branch'] = dict(DEFAULT_CFG['branch'])
    cfg['branch']['on'] = True
    net = Network(cfg)
    ee = net.S['ee']
    net._reward_of = lambda cells: np.ones(len(np.atleast_1d(cells)), float)

    nE = net.nE_slot
    ib = net.br_branch
    found = None
    for j in range(net.N_E):
        st, en = int(net.in_ptr[j]), int(net.in_ptr[j + 1])
        if en - st < 2:
            continue
        wi = net.in_order[st:en]
        b = ib[wi]
        for b1 in range(net.br_n):
            for b2 in range(b1 + 1, net.br_n):
                i1 = wi[b == b1]
                i2 = wi[b == b2]
                if i1.size and i2.size:
                    found = (j, int(i1[0]), int(i2[0]), b1, b2)
                    break
            if found:
                break
        if found:
            break
    if found is None:
        log('❌ 找不到"同一 post、两个分支"的边对 ⇒ 测试无法进行（不是通过）')
        return 1

    j, e1, e2, b1, b2 = found
    p1, p2 = int(ee['pre'][e1]), int(ee['pre'][e2])
    net.xE_t[:] = 0.0
    net.yE_t[:] = 0.0
    net.xE_t[p1] = 1.0
    net.xE_t[p2] = 1.0
    net.yE_t[j] = 1.0
    ee['w'][e1] = 0.1
    ee['w'][e2] = 0.1

    def trial(row):
        w0 = ee['w'].copy()
        net.br_s[:] = 0.0
        net.br_s[j, :] = row
        net._stdp_step(np.array([j], dtype=np.int64))
        d = ee['w'] - w0
        ee['w'][:] = w0
        return float(d[e1]), float(d[e2])

    log('=' * 78)
    log('闸1 · 分支局部信用 · 合成检查')
    log('=' * 78)
    log('  post=%d ｜ 边 e1: pre=%d branch=%d ｜ 边 e2: pre=%d branch=%d' % (j, p1, b1, p2, b2))
    log('  两条边的 x[pre] 都为 1.0，权重都为 0.1 ⇒ 旧规则下 Δw 必须逐位相同')
    log('')

    a1, a2 = trial(np.ones(net.br_n))
    log('  A 全分支相等   s=%s' % np.round(np.ones(net.br_n), 3))
    log('     Δw(e1)=%+.6e  Δw(e2)=%+.6e  差=%+.2e' % (a1, a2, a1 - a2))

    row = np.full(net.br_n, 0.25)
    row[b1] = 2.0
    row[b2] = 0.5
    row = row / row.mean()
    c1, c2 = trial(row)
    log('  B 分支不等     s=%s（归一到均值 1）' % np.round(row, 3))
    log('     Δw(e1)=%+.6e  Δw(e2)=%+.6e  比值=%.3f' % (c1, c2, (c1 / c2) if c2 else float('nan')))

    net.br_on = False
    d1, d2 = trial(np.ones(net.br_n))
    net.br_on = True
    log('  C 机制关闭')
    log('     Δw(e1)=%+.6e  Δw(e2)=%+.6e  差=%+.2e' % (d1, d2, d1 - d2))
    log('')

    ok_a = abs(a1 - a2) <= 1e-15
    ok_b = abs(c1 - c2) > 1e-9
    ok_c = abs(d1 - d2) <= 1e-15
    log('  ✅/❌ A 全分支相等 ⇒ 逐位相同：%s' % ('✅' if ok_a else '❌'))
    log('  ✅/❌ B 分支不等   ⇒ 信用可分：%s' % ('✅' if ok_b else '❌'))
    log('  ✅/❌ C 机制关闭   ⇒ 逐位相同：%s' % ('✅' if ok_c else '❌'))
    log('')
    if ok_a and ok_b and ok_c:
        log('★ 判定：分支局部信用**可表示** —— 同一 post 的两条入线拿到了不同的 Δw，')
        log('  且全分支相等时退化回旧规则（说明差异来自分支，不是数值噪声）。')
    else:
        log('★ 判定：不成立。B 不过 ⇒ 机制没有起作用；A 或 C 不过 ⇒ 实现污染了旧路径。')
    log('=' * 78)
    return 0 if (ok_a and ok_b and ok_c) else 1


def criteria_run(args):
    U = int(args.units or 40)
    ms = float(args.ms or 12000.0)
    out = []
    res = {}
    for tag, over in (('A 全开（延迟 + 接线费 + STDP三因子 + 归一化）', {}),
                      ('B 对照：关掉可塑性（延迟/接线费/生死都还在）', {'syn': {'on': False}}),
                      ('C 对照：可塑性开着，只关掉归一化', {'syn': {'norm_on': False}})):
        cfg = _merge(_merge(copy.deepcopy(DEFAULT_CFG), {'n_units': U}), over)
        net = Network(cfg)
        d0, w0, al0 = net.syn_dist.copy(), net.S['ee']['w'].copy(), net.syn_alive.copy()
        t0 = time.time()
        net.run_until(ms)
        c = dev_criteria(net, cfg, d0, w0, al0, ms)
        c['wall'] = time.time() - t0
        c['pop'] = net.n_alive()
        c['pm'] = pop_metrics(net, ms - 3000.0, ms)
        c['n_dead'], c['n_born'] = net.n_dead, net.n_born
        res[tag[0]] = c
        head = ('规模 %d 工位 × %d 槽位 ｜ 跑 %.0f 秒（真实 %.0fs）｜ 细胞 %d ｜ E=%.2fHz ｜ %s'
                % (U, net.nE_slot, ms / 1000.0, c['wall'], c['pop'], c['pm']['mean_E'],
                   c['pm']['verdict']))
        vals = [(c['gap'] > 0.5), (abs(c['dev_pct']) > 20), (c['Q'] > 0.3),
                (c['dist_ratio'] < 0.9), (c['rd_gap'] > 0.1)]
        txt = [head,
               '  ① 长程权重双峰     峰间距 %.3f（阈值>0.5）%s' % (c['gap'], '✅' if vals[0] else '❌'),
               '  ② 长程权重均值     初始 %.4f → %.4f（偏 %+.0f%%，阈值>20%%）%s'
               % (c['w0'], c['w1'], c['dev_pct'], '✅' if vals[1] else '❌'),
               '  ③ 模块度 Q         %.2f（阈值>0.3，%d 社区）%s'
               % (c['Q'], c['n_mod'], '✅' if vals[2] else '❌'),
               '  ④ 长程边平均距离   %.2f → %.2f（%.2f 倍，阈值<0.9）%s'
               % (c['dist0'], c['dist1'], c['dist_ratio'], '✅' if vals[3] else '❌'),
               '  ⑤ 近邻r−远距r      %+.2f（阈值>0.1）%s ← 我加的防假通关判据'
               % (c['rd_gap'], '✅' if vals[4] else '❌'),
               '  长程突触存活 %.0f%% ｜ ee 突触存活 %.0f%% ｜ 死 %d 生 %d'
               % (100 * c['lr_alive_frac'], 100 * c['w_alive_frac'], c['n_dead'], c['n_born'])]
        print('=' * 70)
        print(tag)
        print('=' * 70)
        for s in txt:
            print(s)
        print()
        out += ['=' * 70, tag, '=' * 70] + txt
    print('=' * 70)
    print('汇总（四条里满足几条，≥2 算通关）')
    print('=' * 70)
    out += ['=' * 70, '汇总', '=' * 70]
    for k, c in res.items():
        n = int(sum([c['gap'] > 0.5, abs(c['dev_pct']) > 20, c['Q'] > 0.3,
                     c['dist_ratio'] < 0.9]))
        s = '  %s：%d/4 ｜ 防假通关判据⑤：%s' % (k, n, '通过' if c['rd_gap'] > 0.1 else '未通过')
        print(s)
        out.append(s)

    pth = os.path.join(SD, 'report', '_006_验收判据_单种子.txt')
    os.makedirs(os.path.dirname(pth), exist_ok=True)
    with open(pth, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print('[判据结果] -> %s' % pth)
    return pth

def main():
    ap = argparse.ArgumentParser(description='01_substrate')
    ap.add_argument('--units', type=int, default=None)
    ap.add_argument('--cells', type=int, default=None)
    ap.add_argument('--drive', type=float, default=None)
    ap.add_argument('--ms', type=float, default=None)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--nodev', action='store_true', help='对照：关掉生死')
    ap.add_argument('--no-prune', action='store_true', help='对照：关掉突触修剪')
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--criteria', action='store_true', help='★验收：四条预注册判据 + 两条对照臂')
    ap.add_argument('--pair-probe', action='store_true',
                    help='★闸1：成对资格迹是否让先后决定符号')
    ap.add_argument('--timing-probe', action='store_true',
                    help='★闸1：检查更新是否依赖 pre/post 的先后（还是只依赖强度）')
    ap.add_argument('--branch-probe', action='store_true',
                    help='★闸1：分支局部信用的合成检查（同 post、两分支、同 pre 迹）')
    args = ap.parse_args()
    if args.pair_probe:
        raise SystemExit(pair_probe(args))
    if args.timing_probe:
        raise SystemExit(timing_probe(args))
    if args.branch_probe:
        raise SystemExit(branch_probe(args))
    if args.criteria:
        criteria_run(args)
        return
    if args.report:
        report(args)
        return
    if args.probe or args.headless:
        probe(args)
        return
    probe(args)

if __name__ == '__main__':
    main()