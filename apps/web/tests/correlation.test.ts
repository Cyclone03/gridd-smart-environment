import { describe, expect, it } from "vitest";
import { analyseAllPairs, pearson, toSeries } from "../src/utils/correlation";
import { history } from "./helpers";

describe("corrélations", () => {
  it("calcule un coefficient de Pearson", () => {
    expect(pearson([1, 2, 3, 4], [2, 4, 6, 8])?.r).toBeCloseTo(1);
    expect(pearson([1, 2, 3, 4], [8, 6, 4, 2])?.r).toBeCloseTo(-1);
    expect(pearson([1, 1, 1], [1, 2, 3])).toBeNull();
  });

  it("aligne les séries sur leurs créneaux communs", () => {
    const temperature = toSeries(history(12), "temperature");
    const humidity = toSeries(
      history(12, {
        type: "humidity",
        points: history(12).points.map((point) => ({ ...point, average: 60 - point.average })),
      }),
      "humidity",
    );
    const [pair] = analyseAllPairs([temperature, humidity]);
    expect(pair.n).toBe(12);
    expect(pair.r).toBeCloseTo(-1);
  });
});
