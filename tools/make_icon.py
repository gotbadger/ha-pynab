"""Generate icon.png for the HACS repository (simple rabbit silhouette, pure stdlib)."""
import math
import struct
import zlib

W = H = 256
SS = 4  # supersample factor


def inside_ellipse(x, y, cx, cy, rx, ry, rot=0.0):
    dx, dy = x - cx, y - cy
    c, s = math.cos(rot), math.sin(rot)
    dx, dy = dx * c + dy * s, -dx * s + dy * c
    return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1.0


def inside(x, y):
    # head
    if inside_ellipse(x, y, 128, 150, 52, 44):
        return True
    # left ear
    if inside_ellipse(x, y, 103, 84, 17, 52, rot=math.radians(-14)):
        return True
    # right ear
    if inside_ellipse(x, y, 153, 84, 17, 52, rot=math.radians(14)):
        return True
    # body base
    if inside_ellipse(x, y, 128, 228, 70, 26):
        return True
    return False


BG = (245, 245, 245)
FG = (96, 62, 32)  # brown rabbit
NOSE = (233, 84, 32)  # orange nose LED


def sample(x, y):
    """Return color for supersampled point."""
    return FG if inside(x, y) else BG


def main():
    rows = []
    for py in range(H):
        row = bytearray()
        row.append(0)  # filter type 0
        for px in range(W):
            # 4x4 supersampling
            r = g = b = n = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = px + (sx + 0.5) / SS
                    y = py + (sy + 0.5) / SS
                    # nose LED: small orange ellipse on head
                    if inside_ellipse(x, y, 128, 150, 14, 10):
                        cr, cg, cb = NOSE
                    else:
                        cr, cg, cb = sample(x, y)
                    r += cr
                    g += cg
                    b += cb
                    n += 1
            row += struct.pack("BBB", r // n, g // n, b // n)
        rows.append(bytes(row))

    raw = b"".join(rows)


    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    with open("icon.png", "wb") as f:
        f.write(png)
    print("icon.png written", len(png), "bytes")


if __name__ == "__main__":
    main()