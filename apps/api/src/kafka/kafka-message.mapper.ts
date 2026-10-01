import { ObservationType } from '../observations/entities/observation.entity';
import { ObservationInput } from '../observations/interfaces/observation-input.interface';

const TOPIC_TYPES: Readonly<Record<string, ObservationType>> = {
  'gridd.obs.environmental.temperature': ObservationType.TEMPERATURE,
  'gridd.obs.environmental.humidity': ObservationType.HUMIDITY,
  'gridd.obs.environmental.co2': ObservationType.CO2,
  'gridd.obs.acoustic.sound_level': ObservationType.SOUND_LEVEL,
  'gridd.obs.occupancy.count': ObservationType.OCCUPANCY,
};

type JsonObject = Record<string, unknown>;

export class InvalidKafkaObservationError extends Error {}

export function mapKafkaObservation(
  topic: string,
  value: Buffer | null,
): ObservationInput {
  if (!value) throw new InvalidKafkaObservationError('message value is empty');

  let payload: unknown;
  try {
    payload = JSON.parse(value.toString('utf8'));
  } catch {
    throw new InvalidKafkaObservationError('message is not valid JSON');
  }
  if (!isObject(payload)) {
    throw new InvalidKafkaObservationError('message must contain a JSON object');
  }

  const expectedType = TOPIC_TYPES[topic];
  if (!expectedType) throw new InvalidKafkaObservationError(`unsupported topic: ${topic}`);

  const nodeId = readString(payload, 'node_id', 'nodeId');
  const type = readString(payload, 'type');
  const unit = readString(payload, 'unit');
  const numericValue = payload.value;
  if (!nodeId) throw new InvalidKafkaObservationError('node_id is required');
  if (type !== expectedType) {
    throw new InvalidKafkaObservationError(
      `type ${type || '<missing>'} is inconsistent with topic ${topic}`,
    );
  }
  if (typeof numericValue !== 'number' || !Number.isFinite(numericValue)) {
    throw new InvalidKafkaObservationError('value must be a finite number');
  }
  if (!unit) throw new InvalidKafkaObservationError('unit is required');

  const rawMetadata = payload.metadata;
  if (rawMetadata !== undefined && rawMetadata !== null && !isObject(rawMetadata)) {
    throw new InvalidKafkaObservationError('metadata must be a JSON object');
  }
  const metadata = isObject(rawMetadata) ? rawMetadata : null;
  const timestamp = payload.timestamp ?? payload.observed_at ?? payload.observedAt;

  return {
    nodeId,
    type: expectedType,
    value: numericValue,
    unit: normalizeUnit(expectedType, unit),
    observedAt: parseTimestamp(timestamp),
    siteId: nestedString(metadata, 'site', 'id'),
    siteLabel: nestedString(metadata, 'site', 'label'),
    buildingId: nestedString(metadata, 'building', 'id'),
    buildingLabel: nestedString(metadata, 'building', 'label'),
    storeyId: nestedString(metadata, 'storey', 'id'),
    storeyLabel: nestedString(metadata, 'storey', 'label'),
    spaceId: nestedString(metadata, 'space', 'id'),
    spaceLabel: nestedString(metadata, 'space', 'label'),
    zoneId: nestedString(metadata, 'zone', 'id'),
    zoneLabel: nestedString(metadata, 'zone', 'label'),
    positionX: nestedNumber(metadata, 'position', 'x'),
    positionY: nestedNumber(metadata, 'position', 'y'),
    positionZ: nestedNumber(metadata, 'position', 'z'),
    metadata,
  };
}

function normalizeUnit(type: ObservationType, unit: string): string {
  if (type === ObservationType.TEMPERATURE && unit === 'C') return '°C';
  return unit;
}

function parseTimestamp(value: unknown): Date | null {
  if (value === undefined || value === null || value === '') return null;
  if (typeof value !== 'string' && typeof value !== 'number') {
    throw new InvalidKafkaObservationError('timestamp must be a string or number');
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new InvalidKafkaObservationError('timestamp is invalid');
  }
  return date;
}

function readString(object: JsonObject, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = object[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

function nestedString(
  metadata: JsonObject | null,
  parent: string,
  key: string,
): string | null {
  const value = metadata?.[parent];
  return isObject(value) ? readString(value, key) : null;
}

function nestedNumber(
  metadata: JsonObject | null,
  parent: string,
  key: string,
): number | null {
  const value = metadata?.[parent];
  const nested = isObject(value) ? value[key] : undefined;
  return typeof nested === 'number' && Number.isFinite(nested) ? nested : null;
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
