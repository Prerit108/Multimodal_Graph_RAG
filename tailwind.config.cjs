const tokens = require("./design-tokens.json");

const gradient = (name) => {
  const item = tokens.color.gradients[name];
  const stops = item.stops.map(({ color, position }) => `${color} ${position}`).join(", ");
  return item.type === "radial"
    ? `radial-gradient(${item.shape}, ${stops})`
    : `linear-gradient(${item.angle}deg, ${stops})`;
};

module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: tokens.color.dark.background,
        paper: tokens.color.dark.text,
        ember: "#E38343",
        "deep-ink": "#0F0C09",
        "warm-cream": "#F5EFE6",
        accent: { ...tokens.color.dark.accent, ...tokens.color.dark.semantic },
        pastel: tokens.color.pastel,
      },
      fontFamily: Object.fromEntries(
        Object.entries(tokens.typography.fontFamilies).map(([name, value]) => [name, [value]]),
      ),
      fontSize: Object.fromEntries(
        Object.entries(tokens.typography.scale).map(([name, value]) => [
          name,
          [value.fontSize, { lineHeight: String(value.lineHeight), letterSpacing: value.letterSpacing }],
        ]),
      ),
      spacing: tokens.layout.spacing,
      borderRadius: tokens.layout.borderRadius,
      boxShadow: {
        ...tokens.color.shadows,
        "lamp-glow": tokens.color.shadows.lampGlow,
        "candle-flicker": tokens.color.shadows.candleFlicker,
        "elevation-1": tokens.color.shadows.elevation1,
        "elevation-2": tokens.color.shadows.elevation2,
        "elevation-3": tokens.color.shadows.elevation3,
        "elevation-4": tokens.color.shadows.elevation4,
        "inner-glow": tokens.color.shadows.innerGlow,
      },
      backgroundImage: {
        "ambient-surface": gradient("ambientSurface"),
        "golden-hour": gradient("goldenHour"),
        "warm-vignette": gradient("warmVignette"),
        "shelf-glow": gradient("shelfGlow"),
      },
      maxWidth: { workspace: tokens.layout.grid.maxWidth },
      transitionTimingFunction: {
        editorial: tokens.aestheticDirection.transitionCurves.default,
        spring: tokens.aestheticDirection.transitionCurves.springy,
      },
    },
  },
  plugins: [],
};
