export function heatmapColor(count: number, maximum: number): string {
  if (count === 0) return "var(--color-close-friends-heatmap-empty)";

  const intensity = Math.sqrt(count / maximum);
  const lowerStopIndex = Math.floor(intensity);
  const colorStops = [
    "--color-close-friends-heatmap-pink",
    "--color-close-friends-heatmap-green",
  ];
  const upperStopIndex = Math.min(lowerStopIndex + 1, colorStops.length - 1);
  const stopFraction = Math.round((intensity - lowerStopIndex) * 100);
  if (stopFraction === 0 || lowerStopIndex === upperStopIndex) {
    return `var(${colorStops[lowerStopIndex]})`;
  }
  return `color-mix(in srgb, var(${colorStops[lowerStopIndex]}) ${100 - stopFraction}%, var(${colorStops[upperStopIndex]}))`;
}
