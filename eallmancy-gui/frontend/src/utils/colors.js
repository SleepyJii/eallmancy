// src/utils/colors.js

// Nice categorical palette (Tableau/D3-inspired)
const BASE_PALETTE = [
  '#4E79A7','#F28E2B','#E15759','#76B7B2','#59A14F',
  '#EDC948','#B07AA1','#FF9DA7','#9C755F','#BAB0AC',
  '#1F77B4','#FF7F0E','#2CA02C','#D62728','#9467BD',
  '#8C564B','#E377C2','#7F7F7F','#BCBD22','#17BECF'
];

// HSL → HEX
function hslToHex(h, s, l) {
  s /= 100; l /= 100;
  const k = n => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = n =>
    l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  const toHex = x => Math.round(255 * x).toString(16).padStart(2, '0');
  return `#${toHex(f(0))}${toHex(f(8))}${toHex(f(4))}`;
}

// Golden-angle hue generator for unlimited colors
function goldenAngleColor(i) {
  const hue = (i * 137.508) % 360;  // spread hues
  const sat = 65;                    // % — tuned for readability
  const light = 55;                  // %
  return hslToHex(hue, sat, light);
}

/** Deterministic color for an integer index (0-based or any int). */
export function colorForIndex(idx) {
  if (idx == null || Number.isNaN(idx)) return '#cccccc';
  const i = Math.abs(Math.trunc(idx));
  if (i < BASE_PALETTE.length) return BASE_PALETTE[i];
  // After the base palette, generate extras but also vary lightness a hair
  const extra = goldenAngleColor(i);
  return extra;
}

/** Convenience: map a list of indices to colors (preserves order). */
export function colorsForIndices(indices = []) {
  return indices.map((i) => colorForIndex(i));
}
