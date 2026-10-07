from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_supplied_artwork_is_used_as_a_valid_multisize_windows_icon():
    png_path = ROOT / "assets" / "aurora_icon.png"
    ico_path = ROOT / "assets" / "aurora_icon.ico"

    with Image.open(png_path) as source:
        assert source.format == "PNG"
        assert source.size == (1254, 1254)

    with Image.open(ico_path) as icon:
        assert icon.format == "ICO"
        assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= icon.ico.sizes()

    spec = (ROOT / "A.U.R.O.R.A.spec").read_text(encoding="utf-8")
    assert 'icon=str(ROOT / "assets" / "aurora_icon.ico")' in spec
