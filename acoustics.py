import numpy as np


def normalize_to_1khz(freq_data, target_db=84.0):
    """
    freq_data: list of dicts [{'x': 20, 'y': 78.5}, ...]
    Shifts the curve so y = target_db at x = 1000 Hz.
    """
    pt_1k = min(freq_data, key=lambda p: abs(p['x'] - 1000))
    offset = target_db - pt_1k['y']
    return [{'x': p['x'], 'y': p['y'] + offset} for p in freq_data]


def get_band_average(freq_data, min_freq, max_freq):
    """Calculates average dB value within a frequency range."""
    pts = [p['y'] for p in freq_data if min_freq <= p['x'] <= max_freq]
    return np.mean(pts) if pts else 84.0


def classify_sound_signature(raw_freq_data):
    """
    Analyzes normalized frequency response and returns a tonal badge classification.
    """
    data = normalize_to_1khz(raw_freq_data)

    sub_bass = get_band_average(data, 20, 60)
    mid_bass = get_band_average(data, 60, 250)
    mids = get_band_average(data, 250, 1000)
    pinna_gain = get_band_average(data, 2000, 4000)
    treble = get_band_average(data, 5000, 10000)

    # Calculate band boosts relative to midrange baseline (84 dB)
    bass_boost = (sub_bass + mid_bass) / 2.0 - mids
    treble_boost = treble - mids
    pinna_boost = pinna_gain - mids

    # Classification Rules
    if bass_boost >= 6.5 and treble_boost >= 3.0:
        return {"tag": "V-Shape", "color": "#7c3aed", "desc": "Fun profile with boosted bass & treble"}

    elif bass_boost >= 7.0 and treble_boost < 2.0:
        return {"tag": "Basshead / Warm", "color": "#2563eb", "desc": "Substantial low-end emphasis with smooth treble"}

    elif bass_boost < 2.5 and treble_boost >= 3.5:
        return {"tag": "Bright / Analytical", "color": "#0284c7",
                "desc": "Emphasized detail & treble extension with flat bass"}

    elif pinna_boost >= 6.5 and bass_boost < 4.0:
        return {"tag": "Mid-Forward / Vocal", "color": "#059669", "desc": "Intimate, vocal-centric profile"}

    elif 3.0 <= bass_boost <= 6.0 and 1.5 <= treble_boost <= 3.0:
        return {"tag": "Harman Neutral", "color": "#16a34a",
                "desc": "Balanced curve following consumer preference targets"}

    else:
        return {"tag": "Warm Neutral", "color": "#d97706", "desc": "Smooth, natural tonal balance"}