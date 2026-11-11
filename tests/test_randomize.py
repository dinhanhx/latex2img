from latex2img.randomize import SCALE_BUCKETS, contrast, sample_colors, sample_rng, sample_scale


def test_rng_is_order_independent():
    assert sample_rng(42, "eq", 3).random() == sample_rng(42, "eq", 3).random()
    assert sample_rng(42, "eq", 3).random() != sample_rng(42, "eq", 4).random()


def test_scale_buckets():
    values = {sample_scale(sample_rng(0, "x", k), 1.0, 3.0) for k in range(500)}
    assert len(values) <= SCALE_BUCKETS and min(values) >= 1.0 and max(values) <= 3.0


def test_contrast_and_colors():
    assert round(contrast("#000000", "#ffffff"), 1) == 21.0
    for k in range(50):
        fg, bg = sample_colors(sample_rng(1, "c", k), 4.5, 0.5)
        assert contrast(fg, bg) >= 4.5
