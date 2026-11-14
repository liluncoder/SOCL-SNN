
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

_ROOT = os.path.dirname(os.path.abspath(__file__))
_DMS = os.path.join(_ROOT, "tools", "_dms_run.py")
if not os.path.exists(_DMS):
    sys.exit(
        "05_prototype.py expects tools/_dms_run.py next to this file.\n"
        "It ships with the repository; if it is missing, restore it from git:\n"
        "    git checkout -- tools/_dms_run.py"
    )
_spec = importlib.util.spec_from_file_location("dms", _DMS)
dms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dms)
M = dms.M
Base = M.TaskNet

N_MOD = 25
AMP = 10.0
N_HOT = 8
STIM_MS = 70.0
NORM_SCALE = 90.0
R_CLIP = 1.5

RSML_AMP = 0.1116

ENG_SCALE = 0.1116 / 0.73862
BETA = 0.05
ALPHA = 0.5
RHO = 0.85
SIGMA = 0.15

class ProtoNet(Base):

    def p_init(self, n_mod=N_MOD, amp=AMP, n_hot=N_HOT, stim_ms=STIM_MS,
               norm_scale=NORM_SCALE, mod_dim=False, fb_proj=False, seed=0,
               rho=RHO, sigma=SIGMA, calib=None, alpha=ALPHA, beta=BETA,
               fb_mode="rand", dcmode="global", tgt_seq=None,
               p_inj="engE", p_sc_fix=None, p_Rmode="engE", p_norm_scale=1.0,
               p_flip_s=False, p_dualcue=False, p_probe_from=None):

        self.p_dualcue = bool(p_dualcue)

        self.p_probe_from = None if p_probe_from is None else int(p_probe_from)

        self.p_norm_scale = float(p_norm_scale)
        self.p_nmod = int(n_mod)
        self.p_amp_max = float(amp)
        self.p_nhot = int(n_hot)
        self.p_stim_ms = float(stim_ms)
        self.p_norm = float(norm_scale)
        self.p_mod_dim = bool(mod_dim)
        self.p_fb = bool(fb_proj)
        self.p_rho = float(rho)
        self.p_sigma = float(sigma)
        self.p_alpha = float(alpha)
        self.p_amp_prev = None

        self.p_base = np.full(self.p_nmod, 1.0) if calib is None else np.asarray(calib["base"], float)
        self.p_scale = np.full(self.p_nmod, float(norm_scale)) if calib is None else np.asarray(calib["scale"], float)

        self.p_beta = float(beta)
        self.p_base_run = np.asarray(self.p_base, float).copy()
        self.p_nbase = 0
        alive = np.nonzero(np.asarray(self.aliveE, bool))[0]
        mod = alive // self.nE_slot
        self.p_cells = [alive[mod == k] for k in range(self.p_nmod)]
        self.p_rng = np.random.default_rng(0x28A0 + int(seed))

        self.p_fbmode = str(fb_mode)

        self.p_dcmode = str(dcmode)
        if self.p_dcmode not in ("global", "permod", "yglob"):
            raise ValueError("unknown dcmode: %r" % (self.p_dcmode,))
        self.p_e_mean = np.zeros(self.p_nmod)
        self.p_ne = 0
        self.p_yglob = 0.0

        if tgt_seq is not None:
            a = np.asarray(tgt_seq, dtype=float)
            if a.ndim != 2 or a.shape[1] != self.p_nmod:
                raise ValueError("tgt_seq shape %r, expected (rounds, %d)" % (a.shape, self.p_nmod))
            self.p_tgt_seq = a
        else:
            self.p_tgt_seq = None
        if self.p_fb:
            if self.p_fbmode == "ident":
                self.p_Wfb = np.eye(self.p_nmod)
            elif self.p_fbmode == "rand":
                self.p_Wfb = self.p_rng.normal(0.0, 1.0 / np.sqrt(self.p_nmod),
                                               size=(self.p_nmod, self.p_nmod))
            elif self.p_fbmode == "mean":

                self.p_Wfb = np.full((self.p_nmod, self.p_nmod), 1.0 / self.p_nmod)
            else:
                raise ValueError("unknown fb_mode: %r" % (self.p_fbmode,))
        else:
            self.p_Wfb = None
        self.p_amp = None
        self.p_hot = None
        self.p_err = np.zeros(self.p_nmod)
        self.p_y = np.zeros(self.p_nmod)
        self.p_y_f = np.zeros(self.p_nmod)
        self.p_cnt0 = np.asarray(self.n_spkE, float).copy()
        self.p_done = False
        self.p_log = []
        self.p_R = np.zeros(self.p_nmod)

        self.p_inj = str(p_inj)
        if self.p_inj not in ("engE", "fb_only", "none", "add"):
            raise ValueError("unknown p_inj: %r" % (self.p_inj,))

        self.p_Eng = np.zeros(np.asarray(self.engE).shape, float)

        self.p_inj_snap = 0.0
        self.p_inj_amp = 0.0

        self.p_sc_fix = None if p_sc_fix is None else max(1e-6, float(p_sc_fix))

        self.p_Rmode = str(p_Rmode)

        self.p_flip_s = bool(p_flip_s)

        if self.p_Rmode not in ("engE", "dir", "flip", "sign", "rand", "abs",
                                "xmod", "xi", "csml", "amp2", "engs", "zero"):
            raise ValueError("unknown p_Rmode: %r" % (self.p_Rmode,))

        self.p_scell = np.zeros(np.asarray(self.engE).shape, float)
        for cells in self.p_cells:
            if cells.size:
                self.p_scell[cells] = np.where(np.arange(cells.size) % 2 == 0, 1.0, -1.0)

        self.p_xicell = np.zeros(np.asarray(self.engE).shape, float)
        if self.p_Rmode in ("rand", "xi", "csml"):
            _rs = np.random.RandomState(0x5CED77)
            for cells in self.p_cells:
                if cells.size:
                    k = cells.size

                    if k % 2:
                        raise ValueError("rand/xi arm needs even cells per module, got %d" % k)
                    v = np.empty(k, float)
                    v[:k // 2] = 1.0
                    v[k // 2:] = -1.0
                    _rs.shuffle(v)
                    self.p_xicell[cells] = v

        self.p_xmod = np.arange(self.p_nmod)
        if self.p_Rmode == "xmod":
            _rs = np.random.RandomState(0x7A1D)
            _id = np.arange(self.p_nmod)
            for _ in range(10000):
                self.p_xmod = _rs.permutation(self.p_nmod)
                if not np.any(self.p_xmod == _id):
                    break
            assert not np.any(self.p_xmod == _id), \
                "xmod needs a derangement (no fixed point), got %s" % (self.p_xmod,)

    def _open_round(self, t):

        if self.p_amp is not None:
            d = np.asarray(self.n_spkE, float) - self.p_cnt0
            self.p_y = np.array([float(d[c].sum()) for c in self.p_cells])
            if self.p_nbase < 5:
                self.p_base_run = self.p_base_run + (self.p_y - self.p_base_run) / (self.p_nbase + 1.0)
            else:
                self.p_base_run = (1.0 - self.p_beta) * self.p_base_run + self.p_beta * self.p_y
            self.p_nbase += 1
            raw = (self.p_y - self.p_base_run) / self.p_scale
            self.p_y_f = (1.0 - self.p_alpha) * self.p_y_f + self.p_alpha * raw
        super()._open_round(t)

        if self.p_probe_from is not None and self._r_idx >= self.p_probe_from:
            if self._phase == 'learn':
                self._phase = 'probe'
                self.n_learn -= 1
                self.n_probe += 1
        if (getattr(self, "p_dualcue", False) and self._dms > 0 and self._dms_cue
                and self.use_marker
                and (self.p_probe_from is None or self._r_idx >= self.p_probe_from)):
            self._hA[2] = 1.0
            self._hA[3] = 1.0

        if self.p_tgt_seq is not None:
            amp = np.array(self.p_tgt_seq[self._r_idx], dtype=float)
        elif self.p_amp is None:
            amp = self.p_rng.uniform(0.0, 0.5 * self.p_amp_max, size=self.p_nmod)
        else:
            noise = self.p_rng.normal(0.0, self.p_sigma * self.p_amp_max, size=self.p_nmod)
            amp = np.clip(self.p_rho * self.p_amp_prev + noise, 0.0, 1.4 * self.p_amp_max)

        tgt = amp / self.p_amp_max
        pred = self.p_y_f.copy()
        self.p_err = tgt - pred

        if self.p_dcmode == "global":
            self.p_err = self.p_err - float(np.mean(self.p_err))
        elif self.p_dcmode == "yglob":

            self.p_yglob = (1.0 - self.p_beta) * self.p_yglob + self.p_beta * float(np.mean(pred))
            self.p_err = tgt - (pred - self.p_yglob)
        else:

            self.p_ne += 1
            if self.p_ne < 5:
                self.p_e_mean = self.p_e_mean + (self.p_err - self.p_e_mean) / float(self.p_ne)
            else:
                self.p_e_mean = (1.0 - self.p_beta) * self.p_e_mean + self.p_beta * self.p_err
            self.p_err = self.p_err - self.p_e_mean

        if self.p_mod_dim and self.p_Wfb is not None:
            self.p_R = np.clip(self.p_Wfb @ self.p_err, -R_CLIP, R_CLIP)

            if getattr(self, "eng_scale_scope", "global") == "act":
                self._snap_calib()
            med, sc = self._calib_pair()
            sc = max(1e-6, float(sc))

            if self.p_sc_fix is not None:
                sc = self.p_sc_fix
            _inj_amp = float(self.r_star) * float(np.mean(np.abs(self.p_R))) * sc

            if self.p_inj == "add":
                _med_all = float(np.median(np.asarray(self.engE)[np.asarray(self.aliveE, bool)]))
                _d = float(self.r_star) * float(sc)
                for k, cells in enumerate(self.p_cells):
                    if cells.size:

                        self.engE[cells] += _d * float(self.p_R[k])
                _inj_amp = float(self.r_star) * float(np.mean(np.abs(self.p_R))) * sc
            elif self.p_inj != "none":
                for k, cells in enumerate(self.p_cells):
                    if cells.size:
                        if self.p_inj == "fb_only":

                            self.p_Eng[cells] = float(med) + float(self.r_star) * float(self.p_R[k]) * sc
                        else:
                            self.engE[cells] = float(med) + float(self.r_star) * float(self.p_R[k]) * sc

            _m = np.asarray(self.aliveE, bool)
            _v = self.engE[_m]
            self.p_inj_snap = float(np.percentile(_v, 75) - np.percentile(_v, 25))
            self.p_inj_amp = _inj_amp
        else:
            self.p_R = np.zeros(self.p_nmod)
            med, sc, _inj_amp = float("nan"), float("nan"), 0.0
            self.p_inj_snap = 0.0
            self.p_inj_amp = 0.0
        self.p_amp = amp
        self.p_amp_prev = amp.copy()
        self.p_hot = np.nonzero(amp > 0.05 * self.p_amp_max)[0]
        self.p_cnt0 = np.asarray(self.n_spkE, float).copy()
        self.p_done = False
        self.p_log.append(dict(i=int(self._r_idx), amp=amp.copy(), err=self.p_err.copy(),
                               y_pred=pred.copy(), R=self.p_R.copy(), cnt=self.p_y.copy(),
                               n_nonzero=int(np.count_nonzero(self.p_err)),
                               inj_snap=float(getattr(self, "p_inj_snap", 0.0)),
                               inj_amp=float(getattr(self, "p_inj_amp", 0.0)),
                               eng_med=float(med), eng_sc=float(sc)))

    def _mem_current(self):
        ie = super()._mem_current()
        if self.p_amp is not None and self._r_t0 is not None:
            t = self.t
            if self._r_t0 <= t < self._r_t0 + self.p_stim_ms:
                for k, cells in enumerate(self.p_cells):
                    a = float(self.p_amp[k])
                    if a > 0.0 and cells.size:
                        ie[cells] += a
        return ie

    def _normalize_weights(self):
        b = getattr(self, "p_norm_scale", 1.0)
        if b == 1.0:
            return super()._normalize_weights()
        orig = self.w_budget_E
        self.w_budget_E = orig * float(b)
        try:
            super()._normalize_weights()
        finally:
            self.w_budget_E = orig

    def _write_reward(self, w_c, s):
        if self.p_mod_dim:
            return None

        if getattr(self, "p_flip_s", False):
            s = -float(s)
        return super()._write_reward(w_c, s)

    def _reward_of(self, cells):
        if getattr(self, "p_Rmode", "engE") == "engE":
            return super()._reward_of(cells)

        c = np.asarray(cells, int)
        mode = self.p_Rmode
        if mode == "zero":

            if c.ndim == 0:
                return 0.0
            return np.zeros(np.asarray(c).shape, float)
        if mode == "engs":

            base = np.asarray(super()._reward_of(cells), float)
            if c.ndim == 0:
                return float(np.clip(ENG_SCALE * float(base), -1.0, 1.0))
            return np.clip(ENG_SCALE * base, -1.0, 1.0)
        if mode == "rand":
            if c.ndim == 0:
                return float(self.p_xicell[int(c)])
            return self.p_xicell[c].copy()
        if mode == "csml":

            if c.ndim == 0:
                return float(RSML_AMP * self.p_xicell[int(c)])
            return float(RSML_AMP) * self.p_xicell[c].copy()
        if mode == "amp2":

            kk3 = np.clip(c // self.nE_slot, 0, self.p_nmod - 1)
            if c.ndim == 0:
                return float(np.clip(-2.0 * float(np.abs(self.p_err[int(kk3)]))
                                     * float(self.p_scell[int(c)]), -1.0, 1.0))
            return np.clip(-2.0 * np.abs(self.p_err[kk3]) * self.p_scell[c], -1.0, 1.0)
        if mode == "xi":

            kk0 = np.clip(c // self.nE_slot, 0, self.p_nmod - 1)
            if c.ndim == 0:
                return float(np.clip(float(self.p_err[int(kk0)])
                                     * float(self.p_xicell[int(c)]), -1.0, 1.0))
            return np.clip(self.p_err[kk0] * self.p_xicell[c], -1.0, 1.0)
        s = self.p_scell[c]
        coef = -self.p_err
        if mode == "flip":
            coef = self.p_err
        if mode == "sign":
            coef = -np.sign(self.p_err)
        if mode == "abs":

            coef = -np.abs(self.p_err)
        if mode == "xmod":

            coef = -np.abs(self.p_err[self.p_xmod])
        if c.ndim == 0:
            k = int(c) // self.nE_slot
            k = min(max(k, 0), self.p_nmod - 1)
            return float(np.clip(float(coef[k]) * float(s), -1.0, 1.0))
        kk = np.clip(c // self.nE_slot, 0, self.p_nmod - 1)
        return np.clip(coef[kk] * s, -1.0, 1.0)

def build_proto(seed=411, **kw):
    calib = kw.pop("calib", None)
    net = M.build(seed=seed, arm=kw.pop("arm", "local"), w_stim=kw.pop("w_stim", 12.0),
                  n_trial=kw.pop("n_trial", 80), round_ms=kw.pop("round_ms", 200.0),
                  choice_mode=kw.pop("choice_mode", "hact"), win_t0=kw.pop("win_t0", 20.0),
                  win_t1=kw.pop("win_t1", 70.0),

                  eng_scale_mode=kw.pop("eng_scale_mode", "legacy"),
                  eng_scale_scope=kw.pop("eng_scale_scope", "global"),
                  mark_gain=1.0, dms=kw.pop("dms", 0),

                  p_safe=kw.pop("p_safe", 0.5),
                  h_decay=kw.pop("h_decay", 1e9), thr_margin=kw.pop("thr_margin", 0.0),
                  r_star=kw.pop("r_star", M.R_STAR0))
    net.__class__ = ProtoNet
    net.p_init(seed=seed, calib=calib, **kw)
    return net

def calibrate(seed=411, rounds=80, **kw):
    import json
    net = build_proto(seed=seed, arm="task_off", **kw)
    t_end = 200.0 * rounds + 50.0
    while net.t < t_end:
        net.step(1)
    log = net.p_log[1:]
    amp = np.array([r["amp"] for r in log]) / net.p_amp_max
    cnt = np.array([r["cnt"] for r in log])
    base = np.zeros(net.p_nmod)
    scale = np.zeros(net.p_nmod)
    r2 = np.zeros(net.p_nmod)
    for k in range(net.p_nmod):
        X = np.stack([np.ones_like(amp[:, k]), amp[:, k]], axis=1)
        coef, *_ = np.linalg.lstsq(X, cnt[:, k], rcond=None)
        base[k], scale[k] = float(coef[0]), float(max(1e-6, coef[1]))
        res = cnt[:, k] - X @ coef
        ss = float(np.sum((cnt[:, k] - cnt[:, k].mean()) ** 2))
        r2[k] = 1.0 - float(np.sum(res ** 2)) / max(1e-9, ss)
    out = dict(seed=int(seed), rounds=len(log), base=base.tolist(), scale=scale.tolist(),
               r2=r2.tolist(), r2_med=float(np.median(r2)), amp_med=float(np.median(amp)))
    return out

def run_proto(seed=411, rounds=320, outdir=None, tag="P", **kw):
    import json
    import time
    net = build_proto(seed=seed, **kw)
    t0 = time.time()
    t_end = 200.0 * rounds + 50.0
    while net.t < t_end:
        net.step(1)
    log = net.p_log[1:]
    err = np.array([r["err"] for r in log])
    y = np.array([r["y_pred"] for r in log])
    amp = np.array([r["amp"] for r in log])
    nz = np.array([r["n_nonzero"] for r in log])
    tgt = amp / net.p_amp_max

    mae_const = float(np.mean(np.abs(tgt - tgt.mean())))

    t1 = tgt[1:]
    tprev = tgt[:-1]
    mae_ar = float(np.mean(np.abs(t1 - net.p_rho * tprev)))
    mae = float(np.mean(np.abs(err)))
    out = dict(seed=int(seed), rounds=len(log), n_mod=int(net.p_nmod),
               mod_dim=bool(net.p_mod_dim), fb=bool(net.p_fb), fb_mode=net.p_fbmode,
               dc_mode=net.p_dcmode,

               wfb_rank=(int(np.linalg.matrix_rank(net.p_Wfb)) if net.p_Wfb is not None else 0),
               wfb_fro2=(float((net.p_Wfb ** 2).sum()) if net.p_Wfb is not None else 0.0),
               mae=mae, mae_const=mae_const, mae_ar=mae_ar,
               gain=float(mae_const - mae), gain_ar=float(mae_ar - mae),
               mae_norm=float(mae / max(1e-9, mae_const)),
               nz_med=float(np.median(nz)), nz_min=int(nz.min()), nz_max=int(nz.max()),
               y_mean=float(y.mean()), y_cv=float(y.std() / max(1e-9, y.mean())),
               tgt_mean=float(tgt.mean()), amp_mean=float(amp.mean()),
               w_md5=dms.md5_of(net.S["ee"]["w"]), wall=float(time.time() - t0),
               n_rounds=int(net._r_idx + 1))

    _Rlog = np.array([r["R"] for r in log]) if log else np.zeros((1, net.p_nmod))
    out["clip_frac"] = float((np.abs(_Rlog) >= R_CLIP - 1e-12).mean())
    out["R_absmax"] = float(np.abs(_Rlog).max())
    out["R_absmean"] = float(np.abs(_Rlog).mean())

    _snap = np.array([r.get("inj_snap", np.nan) for r in log], float)
    _amp = np.array([r.get("inj_amp", np.nan) for r in log], float)
    _ok = np.isfinite(_snap) & np.isfinite(_amp) & (_amp > 0)
    out["inj_iqr_med"] = float(np.median(_snap[_ok])) if _ok.any() else float("nan")
    out["inj_amp_med"] = float(np.median(_amp[_ok])) if _ok.any() else float("nan")

    _scs = np.array([r.get("eng_sc", np.nan) for r in log], float)
    _sok = np.isfinite(_scs) & (_scs > 0)
    out["sc_med"] = float(np.median(_scs[_sok])) if _sok.any() else float("nan")

    out["rho_ratio_med"] = (float(np.median(_snap[_ok] / _amp[_ok])) if _ok.any() else float("nan"))
    out["eng_scale_scope"] = str(getattr(net, "eng_scale_scope", "global"))
    out["p_inj"] = str(getattr(net, "p_inj", "engE"))
    out["p_Rmode"] = str(getattr(net, "p_Rmode", "engE"))

    out["p_flip_s"] = bool(getattr(net, "p_flip_s", False))
    out["r_star"] = float(getattr(net, "r_star", float("nan")))
    if outdir:
        os.makedirs(outdir, exist_ok=True)

        suf = "" if net.p_fbmode == "rand" else "_fb" + net.p_fbmode

        if net.p_dcmode != "global":
            suf += "_dc" + net.p_dcmode
        p = os.path.join(outdir, "%s_s%d_md%d%s.json"
                         % (tag, seed, int(net.p_mod_dim), suf))
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        out["path"] = p
    return out

if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="05_prototype — prototype venue built on the task stage")
    ap.add_argument("--seed", type=int, default=411)
    ap.add_argument("--rounds", type=int, default=320,
                    help="rounds to run; one round is %d ms" % int(200))
    ap.add_argument("--mod-dim", "--mod_dim", dest="mod_dim", action="store_true",
                    help="enable the modulation dimension and the feedback projection")
    ap.add_argument("--dms", type=int, default=0,
                    help="delayed-match delay in rounds (0 = off; >0 populates the "
                         "injection fields of the output)")
    ap.add_argument("--outdir", default=None, help="write the result JSON into this directory")
    ap.add_argument("--tag", default="P", help="filename prefix for --outdir")
    a = ap.parse_args()

    kw = {}
    if a.mod_dim:
        kw["mod_dim"] = True
        kw["fb_proj"] = True
    if a.dms:
        kw["dms"] = int(a.dms)

    o = run_proto(seed=a.seed, rounds=a.rounds, outdir=a.outdir, tag=a.tag, **kw)
    print(json.dumps(o, ensure_ascii=False, indent=1))
