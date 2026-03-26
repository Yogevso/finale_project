export type StructuredLogLevel = 'info' | 'warn' | 'error';
export type StructuredLogContext = Record<string, unknown>;

export interface StructuredLoggerSink {
  info(message: string): void;
  warn(message: string): void;
  error(message: string): void;
}

export interface StructuredLogger {
  info(message: string, context?: StructuredLogContext): void;
  warn(message: string, context?: StructuredLogContext): void;
  error(message: string, context?: StructuredLogContext): void;
  child(scope: string, context?: StructuredLogContext): StructuredLogger;
}

const defaultSink: StructuredLoggerSink = {
  info: (message) => console.log(message),
  warn: (message) => console.warn(message),
  error: (message) => console.error(message),
};

function normalizeValue(value: unknown): unknown {
  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
      stack: value.stack,
    };
  }

  if (Array.isArray(value)) {
    return value.map((entry) => normalizeValue(entry));
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [key, normalizeValue(entry)]),
    );
  }

  return value;
}

function normalizeContext(context: StructuredLogContext | undefined): StructuredLogContext {
  if (!context) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(context).map(([key, value]) => [key, normalizeValue(value)]),
  );
}

export function formatStructuredLogEntry(
  level: StructuredLogLevel,
  scope: string,
  message: string,
  context?: StructuredLogContext,
): string {
  return JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    scope,
    message,
    ...normalizeContext(context),
  });
}

export function createStructuredLogger(
  scope: string,
  sink: StructuredLoggerSink = defaultSink,
  baseContext: StructuredLogContext = {},
): StructuredLogger {
  const emit = (
    level: StructuredLogLevel,
    message: string,
    context?: StructuredLogContext,
  ): void => {
    const payload = formatStructuredLogEntry(level, scope, message, {
      ...baseContext,
      ...(context ?? {}),
    });

    if (level === 'error') {
      sink.error(payload);
      return;
    }

    if (level === 'warn') {
      sink.warn(payload);
      return;
    }

    sink.info(payload);
  };

  return {
    info(message, context) {
      emit('info', message, context);
    },
    warn(message, context) {
      emit('warn', message, context);
    },
    error(message, context) {
      emit('error', message, context);
    },
    child(childScope, context = {}) {
      return createStructuredLogger(
        `${scope}.${childScope}`,
        sink,
        {
          ...baseContext,
          ...context,
        },
      );
    },
  };
}
