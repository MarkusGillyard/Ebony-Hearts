"""Texture authoring in UV space: a numpy rasteriser that maps every texel of a material's UV layout
back to its rest-pose surface point (position, smooth normal, MikkTSpace tangent frame, any per-vertex
attribute), so maps are painted procedurally in 3D and stay seam-free. Also: 3D value noise, normal
maps from 3D perturbations, sampled CC0 detail maps, edge padding and PNG output."""
import math
import os

import bpy
import numpy as np

import eh_mesh as M


# ----------------------------------------------------------------------------- raster

class Raster:
    """Rasterises the UV layout of several objects into one res x res texture space.

    After construction: self.pix (K,) flat texel indices covered; self.P/N/T/B (K,3) float32 rest
    world positions, smooth normals and MikkTSpace tangent/bitangent; self.oid (K,) object index;
    self.bary (K,3); self.tri (K,) triangle index within its object."""

    def __init__(self, objs, res, uv_name="UVMap"):
        self.res = res
        self.objs = objs
        n = res * res
        tri_buf = np.full(n, -1, np.int64)
        oid_buf = np.full(n, -1, np.int16)
        bary_buf = np.zeros((n, 3), np.float32)
        self._tri_data = []
        for oi, ob in enumerate(objs):
            me = ob.data
            if uv_name not in me.uv_layers:
                raise KeyError("%s has no UV layer %s" % (ob.name, uv_name))
            me.uv_layers.active = me.uv_layers[uv_name]
            tv, tl, tp = M.loop_tris(ob)
            uv = M.loop_uvs(ob, uv_name)
            Mw = np.array(ob.matrix_world)
            V = M.co(ob) @ Mw[:3, :3].T + Mw[:3, 3]
            Nv = M.vnormals(ob) @ Mw[:3, :3].T
            Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-12)
            # corner normals for flat-shaded faces fall back to vertex normals (we shade smooth)
            try:
                me.calc_tangents(uvmap=uv_name)
                tan = np.empty(len(me.loops) * 3)
                me.loops.foreach_get("tangent", tan)
                tan = tan.reshape(-1, 3) @ Mw[:3, :3].T
                sgn = np.empty(len(me.loops))
                me.loops.foreach_get("bitangent_sign", sgn)
                me.free_tangents()
            except RuntimeError:
                tan = np.zeros((len(me.loops), 3))
                tan[:, 0] = 1
                sgn = np.ones(len(me.loops))
            self._tri_data.append((tv, tl, V, Nv, tan, sgn))
            self._tri_poly = getattr(self, "_tri_poly", []) + [tp]
            tuv = uv[tl] * res - 0.5          # pixel centres at integer coordinates
            for t in range(len(tv)):
                a, b, c = tuv[t]
                x0 = max(int(math.floor(min(a[0], b[0], c[0]))), 0)
                x1 = min(int(math.ceil(max(a[0], b[0], c[0]))), res - 1)
                y0 = max(int(math.floor(min(a[1], b[1], c[1]))), 0)
                y1 = min(int(math.ceil(max(a[1], b[1], c[1]))), res - 1)
                if x1 < x0 or y1 < y0:
                    continue
                xs = np.arange(x0, x1 + 1)
                ys = np.arange(y0, y1 + 1)
                X, Y = np.meshgrid(xs, ys)
                d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(d) < 1e-12:
                    continue
                l0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
                l1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
                l2 = 1 - l0 - l1
                eps = -0.02
                inside = (l0 >= eps) & (l1 >= eps) & (l2 >= eps)
                if not inside.any():
                    continue
                flat = (Y[inside] * res + X[inside])
                tri_buf[flat] = t
                oid_buf[flat] = oi
                L = np.stack([l0[inside], l1[inside], l2[inside]], 1)
                L = np.clip(L, 0, 1)
                L /= L.sum(1, keepdims=True)
                bary_buf[flat] = L
        self.pix = np.nonzero(tri_buf >= 0)[0]
        self.tri = tri_buf[self.pix]
        self.oid = oid_buf[self.pix].astype(np.int64)
        self.bary = bary_buf[self.pix]
        K = len(self.pix)
        self.P = np.zeros((K, 3), np.float32)
        self.N = np.zeros((K, 3), np.float32)
        self.T = np.zeros((K, 3), np.float32)
        self.B = np.zeros((K, 3), np.float32)
        for oi, (tv, tl, V, Nv, tan, sgn) in enumerate(self._tri_data):
            sel = self.oid == oi
            if not sel.any():
                continue
            t = self.tri[sel]
            L = self.bary[sel][:, :, None]
            self.P[sel] = (V[tv[t]] * L).sum(1)
            n = (Nv[tv[t]] * L).sum(1)
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            self.N[sel] = n
            tg = (tan[tl[t]] * L).sum(1)
            tg -= n * (tg * n).sum(1, keepdims=True)
            tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-12)
            s = np.sign((sgn[tl[t]] * L[:, :, 0]).sum(1))
            s[s == 0] = 1
            self.T[sel] = tg
            self.B[sel] = np.cross(n, tg) * s[:, None]
        self.K = K

    def vattr(self, per_obj):
        """Interpolates per-vertex arrays (list aligned with objs; None -> 0) to texels."""
        first = next(a for a in per_obj if a is not None)
        shape = (self.K,) + np.asarray(first).shape[1:]
        out = np.zeros(shape, np.float32)
        for oi, arr in enumerate(per_obj):
            if arr is None:
                continue
            arr = np.asarray(arr)
            sel = self.oid == oi
            if not sel.any():
                continue
            tv = self._tri_data[oi][0]
            t = self.tri[sel]
            L = self.bary[sel]
            if arr.ndim == 1:
                out[sel] = (arr[tv[t]] * L).sum(1)
            else:
                out[sel] = (arr[tv[t]] * L[:, :, None]).sum(1)
        return out

    def poly(self):
        """Polygon index (within its object) of every texel."""
        out = np.zeros(self.K, np.int64)
        for oi, tp in enumerate(self._tri_poly):
            sel = self.oid == oi
            out[sel] = tp[self.tri[sel]]
        return out

    def islands(self):
        """Global UV-island id of every texel (islands of all objects numbered consecutively)."""
        import eh_garment as G
        out = np.zeros(self.K, np.int64)
        poly = self.poly()
        base = 0
        for oi, ob in enumerate(self.objs):
            ids = G.uv_islands(ob)
            sel = self.oid == oi
            out[sel] = ids[poly[sel]] + base
            base += int(ids.max()) + 1 if len(ids) else 0
        return out

    def grain(self, mpu, up=(0.0, 0.0, 1.0)):
        """Grain-aligned surface coordinates in metres: per UV island the texel frame is turned so +v
        follows world up (projected), so woven/knit detail runs straight down every panel and matches
        across island borders. Returns (gu, gv, cos, sin) with cos/sin of the island's turn (to turn
        sampled tangent-space normals back into the island's UV frame)."""
        isl = self.islands()
        upv = np.asarray(up, np.float32)
        a = np.arctan2(self.T @ upv, self.B @ upv)
        w = np.linalg.norm(np.stack([self.T @ upv, self.B @ upv], 1), axis=1)
        n = isl.max() + 1
        cs = np.bincount(isl, np.cos(a) * w, n)
        sn = np.bincount(isl, np.sin(a) * w, n)
        ang = np.arctan2(sn, cs)[isl]
        uv = self.uv() * mpu
        cen_u = np.bincount(isl, uv[:, 0], n) / np.maximum(np.bincount(isl, None, n), 1)
        cen_v = np.bincount(isl, uv[:, 1], n) / np.maximum(np.bincount(isl, None, n), 1)
        du = uv[:, 0] - cen_u[isl]
        dv = uv[:, 1] - cen_v[isl]
        c, s_ = np.cos(ang), np.sin(ang)
        gu = c * du - s_ * dv
        gv = s_ * du + c * dv
        return gu.astype(np.float32), gv.astype(np.float32), c.astype(np.float32), s_.astype(np.float32)

    def height_normals(self, h, texel_m, strength=1.0):
        """Tangent-space (OpenGL) normal colours from a height field in metres given per texel."""
        img, cov = self.to_image(np.asarray(h, np.float32), 1)
        img = dilate(img, cov, 3)[..., 0]
        gx = (np.roll(img, -1, 1) - np.roll(img, 1, 1)) * 0.5 / texel_m
        gy = (np.roll(img, -1, 0) - np.roll(img, 1, 0)) * 0.5 / texel_m
        n = np.stack([-gx * strength, -gy * strength, np.ones_like(gx)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return n.reshape(-1, 3)[self.pix] * 0.5 + 0.5

    def obj_mask(self, oi):
        return self.oid == oi

    def uv(self):
        y, x = np.divmod(self.pix, self.res)
        return np.stack([(x + 0.5) / self.res, (y + 0.5) / self.res], 1).astype(np.float32)

    def to_image(self, values, channels, fill=None):
        img = np.zeros((self.res * self.res, channels), np.float32)
        if fill is not None:
            img[:] = fill
        img[self.pix] = values.reshape(self.K, channels)
        cov = np.zeros(self.res * self.res, bool)
        cov[self.pix] = True
        return img.reshape(self.res, self.res, channels), cov.reshape(self.res, self.res)

    def tangent_space(self, n_world):
        """World-space normals at texels -> OpenGL tangent-space colours in 0..1."""
        n = n_world / np.maximum(np.linalg.norm(n_world, axis=1, keepdims=True), 1e-12)
        ts = np.stack([(n * self.T).sum(1), (n * self.B).sum(1), (n * self.N).sum(1)], 1)
        ts[:, 2] = np.maximum(ts[:, 2], 0.05)
        ts /= np.linalg.norm(ts, axis=1, keepdims=True)
        return ts * 0.5 + 0.5


# ----------------------------------------------------------------------------- image ops

def dilate(img, cov, iters=16):
    """Edge padding: grows covered texels into empty space so mips and bilinear taps stay clean."""
    img = img.copy()
    cov = cov.copy()
    for _ in range(iters):
        acc = np.zeros_like(img)
        cnt = np.zeros(cov.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sc = np.roll(np.roll(cov, dy, 0), dx, 1)
            si = np.roll(np.roll(img, dy, 0), dx, 1)
            acc += si * sc[..., None]
            cnt += sc
        grow = (~cov) & (cnt > 0)
        if not grow.any():
            break
        img[grow] = acc[grow] / cnt[grow][:, None]
        cov = cov | grow
    # anything still empty takes the mean colour
    if (~cov).any():
        img[~cov] = img[cov].mean(0)
    return img


def save_png(img, path, alpha=False):
    """img: (h, w, c) floats 0..1 already in the encoding wanted on disk (sRGB colour, linear data)."""
    h, w, c = img.shape
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :min(c, 3)] = img[..., :min(c, 3)]
    if c == 1:
        rgba[..., 1] = rgba[..., 2] = img[..., 0]
    if c == 4:
        rgba[..., 3] = img[..., 3]
    name = os.path.splitext(os.path.basename(path))[0]
    im = bpy.data.images.get(name)
    if im is not None:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, w, h, alpha=alpha, float_buffer=False)
    im.colorspace_settings.name = "sRGB"
    im.pixels.foreach_set(np.clip(rgba, 0, 1).ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return path


def load_image(path):
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)


def sample(img, uv, wrap=True):
    """Bilinear sample of (h,w,c) image at uv (K,2) (tiling when wrap)."""
    h, w = img.shape[:2]
    x = uv[:, 0] * w - 0.5
    y = uv[:, 1] * h - 0.5
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[:, None]
    fy = (y - y0)[:, None]
    if wrap:
        xa, xb = x0 % w, (x0 + 1) % w
        ya, yb = y0 % h, (y0 + 1) % h
    else:
        xa, xb = np.clip(x0, 0, w - 1), np.clip(x0 + 1, 0, w - 1)
        ya, yb = np.clip(y0, 0, h - 1), np.clip(y0 + 1, 0, h - 1)
    return ((img[ya, xa] * (1 - fx) + img[ya, xb] * fx) * (1 - fy)
            + (img[yb, xa] * (1 - fx) + img[yb, xb] * fx) * fy)


_MIPS = {}


def mips(key, img):
    """Box-filtered mip chain of an (h, w, c) image (cached by key)."""
    if key not in _MIPS:
        ch = [img]
        while min(ch[-1].shape[:2]) > 4:
            a = ch[-1]
            h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
            a = a[:h, :w]
            ch.append(0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]))
        _MIPS[key] = ch
    return _MIPS[key]


def sample_filtered(key, img, uv, footprint_px):
    """Trilinear sample (tiling) of img at uv with a footprint of `footprint_px` source pixels per
    destination texel: picks/blends the box-filtered mip levels so minified detail never aliases."""
    ch = mips(key, img)
    lod = float(np.clip(np.log2(max(footprint_px, 1e-6)), 0, len(ch) - 1))
    l0 = int(np.floor(lod))
    l1 = min(l0 + 1, len(ch) - 1)
    t = lod - l0
    a = sample(ch[l0], uv)
    if t < 1e-3 or l1 == l0:
        return a
    return a * (1 - t) + sample(ch[l1], uv) * t


def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


# ----------------------------------------------------------------------------- noise

def _hash(ix, iy, iz, seed):
    h = ((ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ ((seed * 2654435761) % 2147483647)) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF)


def vnoise3(P, freq, seed=0):
    p = np.asarray(P, np.float64) * freq
    i = np.floor(p).astype(np.int64)
    f = (p - i).astype(np.float32)
    u = f * f * (3 - 2 * f)
    out = np.zeros(len(p), np.float32)
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1 - u[:, 2]
                out += wx * wy * wz * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out * 2 - 1


def fbm(P, freq, octaves=4, gain=0.5, lac=2.0, seed=0):
    out = np.zeros(len(P), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * vnoise3(P, freq * lac ** o, seed + o * 17)
        tot += amp
        amp *= gain
    return out / tot


def vnoise2(UV, freq, seed=0):
    P = np.zeros((len(UV), 3))
    P[:, :2] = UV
    return vnoise3(P, freq, seed)


# ----------------------------------------------------------------------------- normals

def perturb(N, grad, strength):
    """Surface normal tilted against the tangential part of a 3D height gradient."""
    g = grad - N * (grad * N).sum(1, keepdims=True)
    n = N - g * strength
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def grad3(fn, P, eps=0.0015):
    """Central-difference gradient of a scalar field fn(P) at P."""
    g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3, np.float32)
        d[k] = eps
        g[:, k] = (fn(P + d) - fn(P - d)) / (2 * eps)
    return g


def blend_ts(base, detail, strength=1.0):
    """Reoriented-normal style blend of two tangent-space normals given as 0..1 colours."""
    a = base * 2 - 1
    b = detail * 2 - 1
    b[:, :2] *= strength
    b[:, 2] = np.maximum(b[:, 2], 0.05)
    t = a + np.array([0, 0, 1], np.float32)
    u = b * np.array([-1, -1, 1], np.float32)
    r = t * (t * u).sum(1, keepdims=True) / np.maximum(t[:, 2:3], 1e-4) - u
    r /= np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-12)
    return r * 0.5 + 0.5


# ----------------------------------------------------------------------------- AO

def vertex_ao(target_objs, occluder_objs, rays=24, dist=0.12, seed=1):
    """Per-vertex ambient occlusion (rest pose) by hemisphere ray casts against all occluders."""
    from mathutils import Vector
    col = M.Collider(occluder_objs)
    rng = np.random.default_rng(seed)
    # cosine-weighted hemisphere directions around +Z
    u1 = rng.random(rays)
    u2 = rng.random(rays)
    r = np.sqrt(u1)
    th = 2 * np.pi * u2
    H = np.stack([r * np.cos(th), r * np.sin(th), np.sqrt(1 - u1)], 1)
    out = []
    for ob in target_objs:
        Mw = np.array(ob.matrix_world)
        V = M.co(ob) @ Mw[:3, :3].T + Mw[:3, 3]
        Nn = M.vnormals(ob) @ Mw[:3, :3].T
        Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)
        ao = np.ones(len(V), np.float32)
        bvh = col.bvh
        for i in range(len(V)):
            n = Nn[i]
            a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
            t = np.cross(n, a)
            t /= np.linalg.norm(t)
            b = np.cross(n, t)
            dirs = H[:, :1] * t + H[:, 1:2] * b + H[:, 2:3] * n
            o = Vector(V[i] + n * 0.0015)
            hit = 0
            for d in dirs:
                if bvh.ray_cast(o, Vector(d), dist)[0] is not None:
                    hit += 1
            ao[i] = 1.0 - hit / rays
        out.append(ao)
    return out


# ----------------------------------------------------------------------------- materials

def build_material(name, maps, alpha_clip=False, two_sided=True, sss=0.0, sss_radius=(1.0, 0.35, 0.2),
                   emission=None, specular=0.5):
    """Principled material wired to D (sRGB), N (OpenGL normal), ORM (G=roughness, B=metallic)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.location = (300, 0)
    nt.links.new(p.outputs["BSDF"], out.inputs["Surface"])

    def tex(path, cs, loc):
        n = nt.nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = cs
        n.image = img
        n.location = loc
        return n

    d = tex(maps["D"], "sRGB", (-600, 300))
    nt.links.new(d.outputs["Color"], p.inputs["Base Color"])
    if alpha_clip:
        g = nt.nodes.new("ShaderNodeMath")
        g.operation = "GREATER_THAN"
        g.inputs[1].default_value = 0.5
        g.location = (-200, 400)
        nt.links.new(d.outputs["Alpha"], g.inputs[0])
        nt.links.new(g.outputs[0], p.inputs["Alpha"])
    n = tex(maps["N"], "Non-Color", (-600, -300))
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.location = (-200, -300)
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    o = tex(maps["ORM"], "Non-Color", (-600, 0))
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-250, 0)
    nt.links.new(o.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    p.inputs["Specular IOR Level"].default_value = specular
    if sss > 0:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = sss_radius
        p.inputs["Subsurface Scale"].default_value = 0.012
    mat.use_backface_culling = not two_sided
    try:
        mat.surface_render_method = "DITHERED"
    except AttributeError:
        pass
    return mat
