const SI_PREFIX_MULTIPLIERS: Record<string, number> = {
  Y: 1e24, Z: 1e21, E: 1e18, P: 1e15, T: 1e12,
  G: 1e9, M: 1e6, k: 1e3,
  m: 1e-3, u: 1e-6, µ: 1e-6, n: 1e-9, p: 1e-12,
  f: 1e-15, a: 1e-18, z: 1e-21, y: 1e-24,
};

const NUMBER_WITH_UNIT_RE = /^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*)?$/;

const PREFIXABLE_UNITS = new Set([
  'm', 's', 'A', 'V', 'W', 'Hz', 'F', 'C', 'J', 'N', 'Pa', 'T', 'H', 'S', 'g', 'K', 'Ohm', 'ohm', 'Ω',
]);

/**
 * Parse a string like "1.5 nm" into { numeric: 1.5e-9, unit: "m" }.
 * Returns null if the string does not start with a valid number.
 * The numeric value is scaled to the base SI unit via the prefix.
 */
export function parseNumberWithUnit(text: unknown) {
  const s = String(text ?? '').trim();
  if (!s) return { numeric: 0, unit: '' };

  const m = s.match(NUMBER_WITH_UNIT_RE);
  if (!m) return null;

  const numeric = parseFloat(m[1]);
  const unitStr = (m[2] ?? '').trim();

  if (!unitStr) return { numeric, unit: '' };

  if (unitStr.length >= 2) {
    const prefix = unitStr[0];
    const rest = unitStr.slice(1);
    const multiplier = SI_PREFIX_MULTIPLIERS[prefix];
    if (multiplier !== undefined && PREFIXABLE_UNITS.has(rest)) {
      return { numeric: numeric * multiplier, unit: rest };
    }
  }

  return { numeric, unit: unitStr };
}

const SI_PREFIXES = [
  { exp: -24, prefix: 'y' },
  { exp: -21, prefix: 'z' },
  { exp: -18, prefix: 'a' },
  { exp: -15, prefix: 'f' },
  { exp: -12, prefix: 'p' },
  { exp: -9, prefix: 'n' },
  { exp: -6, prefix: 'u' },
  { exp: -3, prefix: 'm' },
  { exp: 0, prefix: '' },
  { exp: 3, prefix: 'k' },
  { exp: 6, prefix: 'M' },
  { exp: 9, prefix: 'G' },
  { exp: 12, prefix: 'T' },
  { exp: 15, prefix: 'P' },
  { exp: 18, prefix: 'E' },
  { exp: 21, prefix: 'Z' },
  { exp: 24, prefix: 'Y' },
];

const SUPERSCRIPT_DIGITS: Record<string, string> = {
  '-': '⁻',
  '0': '⁰',
  '1': '¹',
  '2': '²',
  '3': '³',
  '4': '⁴',
  '5': '⁵',
  '6': '⁶',
  '7': '⁷',
  '8': '⁸',
  '9': '⁹',
};

export function formatNumericCell(value: unknown) {
  if (value == null) return '';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return String(value);
    const abs = Math.abs(value);
    if (Number.isInteger(value) && abs < 1e6) return String(value);
    if ((abs > 0 && abs < 1e-3) || abs >= 1e4) return value.toExponential(3);
    return value.toFixed(4).replace(/\.?0+$/, '');
  }
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

function toSuperscript(text: string | number) {
  return String(text)
    .split('')
    .map((char) => SUPERSCRIPT_DIGITS[char] || char)
    .join('');
}

export function formatDisplayUnit(unit: unknown) {
  return String(unit ?? '').replace(/\^(-?\d+)/g, (_, exponent) => toSuperscript(exponent));
}

function parsePrefixableUnit(unit: unknown) {
  const text = String(unit ?? '').trim();
  if (!text) return null;

  const poweredMatch = text.match(/^([A-Za-zΩ]+)\^([1-9]\d*)$/);
  if (poweredMatch) {
    const [, baseUnit, powerText] = poweredMatch;
    if (!PREFIXABLE_UNITS.has(baseUnit)) return null;
    return { baseUnit, power: Number.parseInt(powerText, 10) };
  }

  if (!PREFIXABLE_UNITS.has(text)) return null;
  return { baseUnit: text, power: 1 };
}

function formatPrefixedUnit(baseUnit: string, prefix: string, power: number) {
  return power === 1 ? `${prefix}${baseUnit}` : `${prefix}${baseUnit}${toSuperscript(power)}`;
}

function choosePrefixExponent(value: number, power: number) {
  const abs = Math.abs(value);
  const candidates = SI_PREFIXES.map(({ exp, prefix }) => {
    const scaled = value / (10 ** (exp * power));
    return {
      exp,
      prefix,
      scaled,
      absScaled: Math.abs(scaled),
    };
  });

  const inRange = candidates.filter(({ absScaled }) => absScaled >= 1 && absScaled < 999.5);
  if (inRange.length > 0) {
    return inRange.reduce((best, candidate) => (candidate.absScaled < best.absScaled ? candidate : best));
  }

  const aboveOne = candidates.filter(({ absScaled }) => absScaled >= 1);
  if (aboveOne.length > 0) {
    return aboveOne.reduce((best, candidate) => (candidate.absScaled < best.absScaled ? candidate : best));
  }

  return candidates.reduce((best, candidate) => (candidate.absScaled > best.absScaled ? candidate : best));
}

/**
 * Given a representative axis value and a unit string, returns the scale factor
 * and prefixed unit label to use for a whole axis.
 * All tick values should be divided by `scale` before display, and `unitLabel` shown once.
 */
export function getAxisScale(representativeValue: unknown, unit: string) {
  if (!unit || typeof representativeValue !== 'number' || !Number.isFinite(representativeValue) || representativeValue === 0) {
    return { scale: 1, unitLabel: unit || '' };
  }
  const { valueText, unitText } = applySIPrefix(representativeValue, unit);
  const scaled = parseFloat(valueText);
  if (!Number.isFinite(scaled) || scaled === 0) return { scale: 1, unitLabel: unit };
  return { scale: representativeValue / scaled, unitLabel: unitText };
}

export function applySIPrefix(value: unknown, unit: unknown) {
  const formattedUnit = formatDisplayUnit(unit);
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return { valueText: formatNumericCell(value), unitText: formattedUnit };
  }
  if (value === 0) {
    return { valueText: '0', unitText: formattedUnit };
  }

  const parsedUnit = parsePrefixableUnit(unit);
  if (!parsedUnit) {
    return { valueText: formatNumericCell(value), unitText: formattedUnit };
  }

  const chosenPrefix = choosePrefixExponent(value, parsedUnit.power);
  return {
    valueText: formatNumericCell(chosenPrefix.scaled),
    unitText: formatPrefixedUnit(parsedUnit.baseUnit, chosenPrefix.prefix, parsedUnit.power),
  };
}

function getCompanionUnitColumn(column: unknown, row: unknown) {
  if (!row || typeof row !== 'object' || typeof column !== 'string' || column === 'unit') {
    return null;
  }
  const unitColumn = `${column}_unit`;
  return typeof (row as Record<string, unknown>)?.[unitColumn] === 'string' ? unitColumn : null;
}

export function getTableColumns(rows: Array<Record<string, unknown>> | null | undefined) {
  const columns: string[] = [];
  const hiddenColumns = new Set<string>();

  for (const row of rows || []) {
    if (!row || typeof row !== 'object') continue;
    for (const key of Object.keys(row)) {
      if (
        key.endsWith('_unit')
        && key.length > 5
        && Object.prototype.hasOwnProperty.call(row, key.slice(0, -5))
      ) {
        hiddenColumns.add(key);
        continue;
      }
      if (!columns.includes(key)) columns.push(key);
    }
  }

  return columns.filter((column) => !hiddenColumns.has(column));
}

export function formatTableRowCell(row: Record<string, unknown>, column: string) {
  const companionUnitColumn = getCompanionUnitColumn(column, row);
  if (companionUnitColumn) {
    const formatted = applySIPrefix(row?.[column], row?.[companionUnitColumn]);
    return formatted.unitText ? `${formatted.valueText} ${formatted.unitText}` : formatted.valueText;
  }
  if (column === 'value' && typeof row?.unit === 'string') {
    return applySIPrefix(row?.value, row.unit).valueText;
  }
  if (column === 'unit' && typeof row?.unit === 'string') {
    return applySIPrefix(row?.value, row.unit).unitText;
  }
  return formatNumericCell(row?.[column]);
}

// ── Bare SI prefix formatting (no unit awareness) ────────────────────

const _BARE_SI_PREFIXES = [
  { prefix: 'T', factor: 1e12 },
  { prefix: 'G', factor: 1e9 },
  { prefix: 'M', factor: 1e6 },
  { prefix: 'k', factor: 1e3 },
  { prefix: '',  factor: 1 },
  { prefix: 'm', factor: 1e-3 },
  { prefix: 'μ', factor: 1e-6 },
  { prefix: 'n', factor: 1e-9 },
  { prefix: 'p', factor: 1e-12 },
  { prefix: 'f', factor: 1e-15 },
];

export function formatSI(v: number, prec: number | null | undefined) {
  if (!Number.isFinite(v)) return String(v);
  if (v === 0) return prec != null ? `0.${'0'.repeat(prec)}` : '0';
  const abs = Math.abs(v);
  let chosen = _BARE_SI_PREFIXES[_BARE_SI_PREFIXES.length - 1];
  for (const p of _BARE_SI_PREFIXES) {
    if (abs >= p.factor * (1 - 1e-10)) { chosen = p; break; }
  }
  const scaled = v / chosen.factor;
  return (prec != null ? scaled.toFixed(prec) : String(scaled)) + chosen.prefix;
}

export function parseSI(text: string) {
  const t = (text || '').trim();
  if (!t) return NaN;
  const lastChar = t.slice(-1);
  const factor = SI_PREFIX_MULTIPLIERS[lastChar];
  if (factor != null) {
    const num = parseFloat(t.slice(0, -1));
    if (!isNaN(num)) return num * factor;
  }
  return parseFloat(t);
}
