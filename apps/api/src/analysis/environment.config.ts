import { registerAs } from '@nestjs/config';

const numeric = (name: string, fallback: number): number => {
  const value = Number(process.env[name]);
  return Number.isFinite(value) ? value : fallback;
};

export default registerAs('environmentAnalysis', () => ({
  thresholds: {
    temperature: {
      warningMin: numeric('TEMPERATURE_WARNING_MIN', 18),
      normalMin: numeric('TEMPERATURE_NORMAL_MIN', 20),
      normalMax: numeric('TEMPERATURE_NORMAL_MAX', 25),
      warningMax: numeric('TEMPERATURE_WARNING_MAX', 28),
    },
    humidity: {
      warningMin: numeric('HUMIDITY_WARNING_MIN', 20),
      normalMin: numeric('HUMIDITY_NORMAL_MIN', 30),
      normalMax: numeric('HUMIDITY_NORMAL_MAX', 60),
      warningMax: numeric('HUMIDITY_WARNING_MAX', 70),
    },
    co2: {
      normalMax: numeric('CO2_NORMAL_MAX', 800),
      warningMax: numeric('CO2_WARNING_MAX', 1200),
    },
    soundLevel: {
      normalMax: numeric('SOUND_LEVEL_NORMAL_MAX', 55),
      warningMax: numeric('SOUND_LEVEL_WARNING_MAX', 70),
    },
  },
  weights: {
    temperature: numeric('COMFORT_WEIGHT_TEMPERATURE', 0.3),
    humidity: numeric('COMFORT_WEIGHT_HUMIDITY', 0.2),
    co2: numeric('COMFORT_WEIGHT_CO2', 0.3),
    noise: numeric('COMFORT_WEIGHT_NOISE', 0.2),
  },
  status: {
    goodMin: numeric('COMFORT_STATUS_GOOD_MIN', 80),
    warningMin: numeric('COMFORT_STATUS_WARNING_MIN', 50),
  },
}));
