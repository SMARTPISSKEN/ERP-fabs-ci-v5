// Génère une référence métier (Sprint 0)
// type: 'commande' | 'facture' | 'bl' | 'br' | 'reglement'
// seq: numéro séquentiel (ex: 1, 12, 345)

const SCHOOL_YEAR_SHORT = "26-27"; // 2026-2027
const CIVIL_YEAR = 2026;

const PREFIX = {
  commande: `FABS-CMD-${SCHOOL_YEAR_SHORT}`,
  facture: `FABS-FC-${SCHOOL_YEAR_SHORT}`,
  bl: `FABS-BL-${SCHOOL_YEAR_SHORT}`,
  br: `FABS-BR-${SCHOOL_YEAR_SHORT}`,
  reglement: `FABS-REG-${CIVIL_YEAR}`,
};

export function generateRef(type, seq) {
  const prefix = PREFIX[type];
  if (!prefix) throw new Error(`Type de document inconnu: ${type}`);
  const padded = String(seq).padStart(4, "0");
  return `${prefix}-${padded}`;
}

export const NUMBERING_PREFIXES = PREFIX;
