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

const PREFIXABLE_UNITS = new Set([
  'm', 's', 'A', 'V', 'W', 'Hz', 'F', 'C', 'J', 'N', 'Pa', 'T', 'H', 'S', 'g', 'K', 'Ohm', 'ohm', 'Ω',
]);

const SUPERSCRIPT_DIGITS = {
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

export function formatNumericCell(value) {
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

function toSuperscript(text) {
  return String(text)
    .split('')
    .map((char) => SUPERSCRIPT_DIGITS[char] || char)
    .join('');
}

export function formatDisplayUnit(unit) {
  return String(unit ?? '').replace(/\^(-?\d+)/g, (_, exponent) => toSuperscript(exponent));
}

function parsePrefixableUnit(unit) {
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

function formatPrefixedUnit(baseUnit, prefix, power) {
  return power === 1 ? `${prefix}${baseUnit}` : `${prefix}${baseUnit}${toSuperscript(power)}`;
}

function choosePrefixExponent(value, power) {
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

export function applySIPrefix(value, unit) {
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

function getCompanionUnitColumn(column, row) {
  if (!row || typeof row !== 'object' || typeof column !== 'string' || column === 'unit') {
    return null;
  }
  const unitColumn = `${column}_unit`;
  return typeof row?.[unitColumn] === 'string' ? unitColumn : null;
}

export function getTableColumns(rows) {
  const columns = [];
  const hiddenColumns = new Set();

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

export function formatTableRowCell(row, column) {
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
