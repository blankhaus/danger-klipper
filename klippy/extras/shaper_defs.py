# Definitions of the supported input shapers
#
# Copyright (C) 2020-2023  Dmitry Butyugin <dmbutyugin@google.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import collections, math

SHAPER_VIBRATION_REDUCTION = 20.0
DEFAULT_DAMPING_RATIO = 0.1

InputShaperCfg = collections.namedtuple(
    "InputShaperCfg", ("name", "init_func", "min_freq")
)
InputSmootherCfg = collections.namedtuple(
    "InputSmootherCfg", ("name", "init_func", "min_freq")
)


def get_none_shaper():
    return ([], [])


def get_zv_shaper(shaper_freq, damping_ratio):
    df = math.sqrt(1.0 - damping_ratio**2)
    K = math.exp(-damping_ratio * math.pi / df)
    t_d = 1.0 / (shaper_freq * df)
    A = [1.0, K]
    T = [0.0, 0.5 * t_d]
    return (A, T)


def get_zvd_shaper(shaper_freq, damping_ratio):
    df = math.sqrt(1.0 - damping_ratio**2)
    K = math.exp(-damping_ratio * math.pi / df)
    t_d = 1.0 / (shaper_freq * df)
    A = [1.0, 2.0 * K, K**2]
    T = [0.0, 0.5 * t_d, t_d]
    return (A, T)


def get_mzv_shaper(shaper_freq, damping_ratio):
    df = math.sqrt(1.0 - damping_ratio**2)
    K = math.exp(-0.75 * damping_ratio * math.pi / df)
    t_d = 1.0 / (shaper_freq * df)

    a1 = 1.0 - 1.0 / math.sqrt(2.0)
    a2 = (math.sqrt(2.0) - 1.0) * K
    a3 = a1 * K * K

    A = [a1, a2, a3]
    T = [0.0, 0.375 * t_d, 0.75 * t_d]
    return (A, T)


def get_ei_shaper(shaper_freq, damping_ratio):
    v_tol = 1.0 / SHAPER_VIBRATION_REDUCTION  # vibration tolerance
    df = math.sqrt(1.0 - damping_ratio**2)
    t_d = 1.0 / (shaper_freq * df)
    dr = damping_ratio

    a1 = (0.24968 + 0.24961 * v_tol) + (
        (0.80008 + 1.23328 * v_tol) + (0.49599 + 3.17316 * v_tol) * dr
    ) * dr
    a3 = (0.25149 + 0.21474 * v_tol) + (
        (-0.83249 + 1.41498 * v_tol) + (0.85181 - 4.90094 * v_tol) * dr
    ) * dr
    a2 = 1.0 - a1 - a3

    t2 = (
        0.4999
        + (
            ((0.46159 + 8.57843 * v_tol) * v_tol)
            + (
                ((4.26169 - 108.644 * v_tol) * v_tol)
                + ((1.75601 + 336.989 * v_tol) * v_tol) * dr
            )
            * dr
        )
        * dr
    )

    A = [a1, a2, a3]
    T = [0.0, t2 * t_d, t_d]
    return (A, T)


def _get_shaper_from_expansion_coeffs(shaper_freq, damping_ratio, t, a):
    tau = 1.0 / shaper_freq
    T = []
    A = []
    n = len(a)
    k = len(a[0])
    for i in range(n):
        u = t[i][k - 1]
        v = a[i][k - 1]
        for j in range(k - 1):
            u = u * damping_ratio + t[i][k - j - 2]
            v = v * damping_ratio + a[i][k - j - 2]
        T.append(u * tau)
        A.append(v)
    return (A, T)


def get_2hump_ei_shaper(shaper_freq, damping_ratio):
    t = [
        [0.0, 0.0, 0.0, 0.0],
        [0.49890, 0.16270, -0.54262, 6.16180],
        [0.99748, 0.18382, -1.58270, 8.17120],
        [1.49920, -0.09297, -0.28338, 1.85710],
    ]
    a = [
        [0.16054, 0.76699, 2.26560, -1.22750],
        [0.33911, 0.45081, -2.58080, 1.73650],
        [0.34089, -0.61533, -0.68765, 0.42261],
        [0.15997, -0.60246, 1.00280, -0.93145],
    ]
    return _get_shaper_from_expansion_coeffs(shaper_freq, damping_ratio, t, a)


def get_3hump_ei_shaper(shaper_freq, damping_ratio):
    t = [
        [0.0, 0.0, 0.0, 0.0],
        [0.49974, 0.23834, 0.44559, 12.4720],
        [0.99849, 0.29808, -2.36460, 23.3990],
        [1.49870, 0.10306, -2.01390, 17.0320],
        [1.99960, -0.28231, 0.61536, 5.40450],
    ]
    a = [
        [0.11275, 0.76632, 3.29160 - 1.44380],
        [0.23698, 0.61164, -2.57850, 4.85220],
        [0.30008, -0.19062, -2.14560, 0.13744],
        [0.23775, -0.73297, 0.46885, -2.08650],
        [0.11244, -0.45439, 0.96382, -1.46000],
    ]
    return _get_shaper_from_expansion_coeffs(shaper_freq, damping_ratio, t, a)


def get_shaper_offset(A, T):
    if not A:
        return 0.0
    return sum([a * t for a, t in zip(A, T)]) / sum(A)


def init_smoother(coeffs, smooth_time, normalize_coeffs):
    if not normalize_coeffs:
        return (list(reversed(coeffs)), smooth_time)
    inv_t_sm = inv_t_sm_n = 1.0 / smooth_time
    n = len(coeffs)
    c = [0] * n
    for i in range(n - 1, -1, -1):
        c[n - i - 1] = coeffs[i] * inv_t_sm_n
        inv_t_sm_n *= inv_t_sm
    return (c, smooth_time)


def get_none_smoother():
    return ([1.0], 0.0)


# Input smoother is a polynomial function w(t) which is convolved with the input
# trajectory x(t) as x_sm(T) = integral(x(t) * w(T-t) * dt, t=[T-T_sm...T+T_sm])
# to obtain a modified trajectory which has low residual vibrations in a certain
# frequency range. Similar to discrete input shapers, the amplitude of residual
# vibrations of a step input signal can be calculated as
# *) V_c = integral(exp(-zeta * omega * t) * cos(omega_d * t) *
#                   * w(T_sm/2 - t) * dt, t=[0...T_sm])
# *) V_s = integral(exp(-zeta * omega * t) * sin(omega_d * t) *
#                   * w(T_sm/2 - t) * dt, t=[0...T_sm])
# *) V = sqrt(V_c^2 + V_s^)
#
# The input smoothers defined below were calculated and optimized in the Maxima
# algebra system by calculating V(w, T_sm, omega, zeta) in a closed form for
# several (depending on smoother) omega_i, zeta_i pairs and optimizing T_sm,
# omega_i, and zeta_i in order to obtain a polynomial w(t) with a minimal T_sm
# such that w(t) >= 0 and V(omega) <= 0.05 in a certain frequency range.
#
# Additional constraints that were enforced for w(t) during optimization:
# *) integral(w(t) * dt, t=[-T_sm/2...T_sm/2]) = 1
# *) w(-T_sm/2) = w(T_sm/2) = 0
# The first condition ensures unity norm of w(t) and the second one makes the
# input smoothers usable as extruder smoothers (for the ease of synchronization
# of the extruder with the toolhead motion).


def get_zv_smoother(
    shaper_freq, damping_ratio_unused=None, normalize_coeffs=True
):
    coeffs = [
        -118.4265334338076,
        5.861885495127615,
        29.52796003014231,
        -1.465471373781904,
        0.01966833207740377,
    ]
    return init_smoother(coeffs, 0.8025 / shaper_freq, normalize_coeffs)


def get_mzv_smoother(
    shaper_freq, damping_ratio_unused=None, normalize_coeffs=True
):
    coeffs = [
        -1906.717580206364,
        125.8892756660212,
        698.0200035767849,
        -37.75923018121473,
        -62.18762409216703,
        1.57172781617736,
        1.713117990217123,
    ]
    return init_smoother(coeffs, 0.95625 / shaper_freq, normalize_coeffs)


def get_ei_smoother(
    shaper_freq, damping_ratio_unused=None, normalize_coeffs=True
):
    coeffs = [
        -1797.048868963208,
        120.5310596109878,
        669.6653197989012,
        -35.71975707450795,
        -62.49388325512682,
        1.396748042940248,
        1.848276903900512,
    ]
    return init_smoother(coeffs, 1.06625 / shaper_freq, normalize_coeffs)


def get_2hump_ei_smoother(
    shaper_freq, damping_ratio_unused=None, normalize_coeffs=True
):
    coeffs = [
        -22525.88434486782,
        2524.826047114184,
        10554.22832043971,
        -1051.778387878068,
        -1475.914693073253,
        121.2177946817349,
        57.95603221424528,
        -4.018706414213658,
        0.8375784787864095,
    ]
    return init_smoother(coeffs, 1.14875 / shaper_freq, normalize_coeffs)


def get_si_smoother(
    shaper_freq, damping_ratio_unused=None, normalize_coeffs=True
):
    coeffs = [
        -6186.76006449789,
        1206.747198930197,
        2579.985143622855,
        -476.8554763069169,
        -295.546608490564,
        52.69679971161049,
        4.234582468800491,
        -2.226157642004671,
        1.267781046297883,
    ]
    return init_smoother(coeffs, 1.245 / shaper_freq, normalize_coeffs)


def get_zvd_ei_smoother(
    shaper_freq, damping_ratio_unused=None, normalize_coeffs=True
):
    coeffs = [
        -18835.07746719777,
        1914.349309746547,
        8786.608981369287,
        -807.3061869131075,
        -1209.429748155012,
        96.48879052981883,
        43.1595785340444,
        -3.577268915175282,
        1.083220648523371,
    ]
    return init_smoother(coeffs, 1.475 / shaper_freq, normalize_coeffs)


def get_smoother_offset(C, t_sm, normalized=True):
    int_t0 = int_t1 = 0.0
    if normalized:
        for i, c in enumerate(C):
            if i & 1:
                int_t1 += c * t_sm ** (i + 2) / (2 ** (i + 1) * (i + 2))
            else:
                int_t0 += c * t_sm ** (i + 1) / (2**i * (i + 1))
    else:
        for i, c in enumerate(C):
            if i & 1:
                int_t1 += c / (2 ** (i + 1) * (i + 2))
            else:
                int_t0 += c / (2**i * (i + 1))
        int_t1 *= t_sm
    return int_t1 / int_t0


# min_freq for each shaper is chosen to have projected max_accel ~= 1500
INPUT_SHAPERS = [
    InputShaperCfg("zv", get_zv_shaper, min_freq=21.0),
    InputShaperCfg("mzv", get_mzv_shaper, min_freq=23.0),
    InputShaperCfg("zvd", get_zvd_shaper, min_freq=29.0),
    InputShaperCfg("ei", get_ei_shaper, min_freq=29.0),
    InputShaperCfg("2hump_ei", get_2hump_ei_shaper, min_freq=39.0),
    InputShaperCfg("3hump_ei", get_3hump_ei_shaper, min_freq=48.0),
]

# min_freq for each smoother is chosen to have projected max_accel ~= 1000
INPUT_SMOOTHERS = [
    InputSmootherCfg("smooth_zv", get_zv_smoother, min_freq=18.0),
    InputSmootherCfg("smooth_mzv", get_mzv_smoother, min_freq=20.0),
    InputSmootherCfg("smooth_ei", get_ei_smoother, min_freq=21.0),
    InputSmootherCfg("smooth_2hump_ei", get_2hump_ei_smoother, min_freq=21.5),
    InputSmootherCfg("smooth_zvd_ei", get_zvd_ei_smoother, min_freq=26.0),
    InputSmootherCfg("smooth_si", get_si_smoother, min_freq=21.5),
]
