import React from "react";

/**
 * Logo officiel EDITIONS FABS-CI — recréé en SVG fidèle.
 * 5 carrés arrondis disposés en asymétrie + texte multicolore.
 *
 * variant="light" → fond clair (textes foncés)
 * variant="dark"  → fond sombre (textes blancs)
 * size="sm" | "md" | "lg"
 */
export default function Logo({ variant = "light", size = "md", className = "" }) {
  const dimensions = {
    sm: { wrap: "h-9", iconBox: 36, textSize: 14 },
    md: { wrap: "h-14", iconBox: 56, textSize: 20 },
    lg: { wrap: "h-24", iconBox: 96, textSize: 32 },
  }[size];

  const darkText = variant === "dark";
  const colorE = darkText ? "#FFFFFF" : "#0A2540"; // letters E,D,I,T,I,O,N,S, -CI
  const colorB = darkText ? "#FFFFFF" : "#3A3A3A"; // letter B (dark grey)

  return (
    <div
      className={`inline-flex items-center gap-3 ${dimensions.wrap} ${className}`}
      data-testid="fabsci-logo"
    >
      {/* Pictogramme - 5 carrés arrondis disposés en grille asymétrique */}
      <svg
        width={dimensions.iconBox}
        height={dimensions.iconBox}
        viewBox="0 0 64 64"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
        aria-label="FABSCI"
      >
        {/* Carré gris (haut-gauche) */}
        <rect x="2" y="14" width="22" height="30" rx="5" fill="#3A3A3A" />
        {/* Carré bleu (centre-gauche, grand) */}
        <rect x="26" y="6" width="22" height="34" rx="5" fill="#0A1FA8" />
        {/* Carré rouge (haut-droite, petit) */}
        <rect x="50" y="2" width="12" height="16" rx="3" fill="#C62828" />
        {/* Carré orange (centre-droite, grand) */}
        <rect x="26" y="40" width="22" height="22" rx="5" fill="#FF6200" />
        {/* Carré noir (bas-centre, petit) */}
        <rect x="38" y="56" width="10" height="8" rx="2" fill="#111111" />
      </svg>

      {/* Texte multicolore : EDITIONS (foncé) — F(orange) A(navy) B(gris) S(rouge) -CI(foncé) */}
      <svg
        viewBox="0 0 200 60"
        xmlns="http://www.w3.org/2000/svg"
        className="h-full"
        preserveAspectRatio="xMinYMid meet"
        aria-label="EDITIONS FABS-CI"
      >
        <text
          x="0"
          y="24"
          fontFamily="Manrope, 'IBM Plex Sans', sans-serif"
          fontSize={dimensions.textSize}
          fontWeight="900"
          fill={colorE}
          letterSpacing="-0.5"
        >
          EDITIONS
        </text>
        <g
          fontFamily="Manrope, 'IBM Plex Sans', sans-serif"
          fontSize={dimensions.textSize + 4}
          fontWeight="900"
          letterSpacing="-0.5"
        >
          <text x="0" y="52" fill="#FF6200">F</text>
          <text x={dimensions.textSize * 0.8} y="52" fill="#0A1FA8">A</text>
          <text x={dimensions.textSize * 1.65} y="52" fill={colorB}>B</text>
          <text x={dimensions.textSize * 2.5} y="52" fill="#C62828">S</text>
          <text x={dimensions.textSize * 3.25} y="52" fill={colorE}>-CI</text>
        </g>
      </svg>
    </div>
  );
}
