db = db.getSiblingDB("kocaeli_news");

const MANDATORY_CATEGORIES = [
  "trafik_kazasi",
  "yangin",
  "elektrik_kesintisi",
  "hirsizlik",
  "kulturel_etkinlik",
  "unknown",
];

const SOURCE_WHITELIST = [
  "cagdaskocaeli.com.tr",
  "ozgurkocaeli.com.tr",
  "seskocaeli.com",
  "yenikocaeli.com",
  "bizimyaka.com",
];

function ensureCollection(name, options) {
  const exists = db.getCollectionNames().includes(name);
  const opts = options || {};

  if (!exists) {
    db.createCollection(name, opts);
    return;
  }

  if (opts.validator) {
    db.runCommand({
      collMod: name,
      validator: opts.validator,
      validationLevel: opts.validationLevel || "strict",
      validationAction: opts.validationAction || "error",
    });
  }
}

function ensureIndex(collection, keys, options) {
  db.getCollection(collection).createIndex(keys, options || {});
}

// 1) SOURCES
ensureCollection("sources", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "domain",
        "display_name",
        "base_url",
        "scraper_type",
        "region",
        "local_source",
        "active",
        "created_at",
        "updated_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        domain: { bsonType: "string" },
        display_name: { bsonType: "string" },
        base_url: { bsonType: "string", pattern: "^https?://" },
        scraper_type: { enum: ["static", "dynamic", "rss", "api"] },
        region: { enum: ["Kocaeli"] },
        language: { bsonType: "string" },
        local_source: { bsonType: "bool" },
        active: { bsonType: "bool" },
        success_rate_7d: {
          bsonType: ["double", "int", "decimal"],
          minimum: 0,
          maximum: 1,
        },
        avg_parse_latency_ms: {
          bsonType: ["double", "int", "long", "decimal"],
          minimum: 0,
        },
        last_success_at: { bsonType: "date" },
        last_failure_at: { bsonType: "date" },
        notes: { bsonType: "string" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex("sources", { domain: 1 }, { name: "domain_unique", unique: true });
ensureIndex("sources", { active: 1, domain: 1 }, { name: "active_domain" });

// 2) CRAWL_SESSIONS
ensureCollection("crawl_sessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "source_id",
        "trigger_type",
        "scope",
        "lookback_days",
        "started_at",
        "status",
        "fetched_count",
        "parsed_count",
        "failed_count",
        "error_summary",
        "created_at",
        "updated_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        source_id: { bsonType: "objectId" },
        trigger_type: { enum: ["startup", "manual", "scheduled"] },
        scope: { enum: ["single_source", "all_sources"] },
        lookback_days: { bsonType: ["int", "long"], minimum: 1, maximum: 30 },
        requested_window_start: { bsonType: "date" },
        requested_window_end: { bsonType: "date" },
        status: {
          enum: [
            "running",
            "success",
            "partial",
            "failed",
            "cancelled",
            "timeout",
          ],
        },
        started_at: { bsonType: "date" },
        ended_at: { bsonType: "date" },
        fetched_count: { bsonType: ["int", "long"], minimum: 0 },
        parsed_count: { bsonType: ["int", "long"], minimum: 0 },
        failed_count: { bsonType: ["int", "long"], minimum: 0 },
        error_summary: {
          bsonType: "array",
          items: {
            bsonType: "object",
            additionalProperties: false,
            required: ["code", "message"],
            properties: {
              code: { bsonType: "string" },
              message: { bsonType: "string" },
              sample_url: { bsonType: "string", pattern: "^https?://" },
            },
          },
        },
        worker_version: { bsonType: "string" },
        trace_id: { bsonType: "string" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex(
  "crawl_sessions",
  { source_id: 1, started_at: -1 },
  { name: "source_started_at" },
);
ensureIndex(
  "crawl_sessions",
  { status: 1, started_at: -1 },
  { name: "status_started_at" },
);
ensureIndex(
  "crawl_sessions",
  { created_at: 1 },
  { name: "ttl_90days", expireAfterSeconds: 7776000 },
);

// 3) RAW_DOCUMENTS
ensureCollection("raw_documents", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "source_id",
        "crawl_session_id",
        "canonical_url",
        "resolved_url",
        "domain",
        "title_raw",
        "text_raw",
        "scraped_at",
        "content_hash",
        "fetch_status",
        "parser_version",
        "schema_version",
        "created_at",
        "updated_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        source_id: { bsonType: "objectId" },
        crawl_session_id: { bsonType: "objectId" },
        canonical_url: { bsonType: "string", pattern: "^https?://" },
        resolved_url: { bsonType: "string", pattern: "^https?://" },
        domain: { bsonType: "string" },
        title_raw: { bsonType: "string" },
        text_raw: { bsonType: "string" },
        content_raw: { bsonType: "string" },
        html_raw_path: { bsonType: "string" },
        screenshot_path: { bsonType: "string" },
        published_at_raw: { bsonType: ["date", "null"] },
        author_raw: { bsonType: ["string", "null"] },
        image_urls_raw: {
          bsonType: "array",
          items: { bsonType: "string", pattern: "^https?://" },
        },
        language: { bsonType: ["string", "null"] },
        content_hash: { bsonType: "string" },
        fetch_status: { enum: ["success", "partial", "failed"] },
        parser_version: { bsonType: "string" },
        schema_version: { bsonType: "string" },
        scraped_at: { bsonType: "date" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex("raw_documents", { canonical_url: 1 }, { name: "canonical_url" });
ensureIndex(
  "raw_documents",
  { source_id: 1, scraped_at: -1 },
  { name: "source_scraped_at" },
);
ensureIndex("raw_documents", { content_hash: 1 }, { name: "content_hash" });
ensureIndex(
  "raw_documents",
  { crawl_session_id: 1 },
  { name: "crawl_session_id" },
);

// 4) SOURCE_RECORDS
// NOTE:
// Atlas UI üzerinden source_records koleksiyonu için Vector Search index(ler)i oluşturulacaktır.
//
// Birincil index:
// - Index adı: source_records_text_embedding_vector
// - Alan: text_embedding
// - Boyut: 1024
// - Similarity: cosine
//
// Opsiyonel ikinci index:
// - Index adı: source_records_image_embedding_vector
// - Alan: image_embedding
// - Boyut: 768
// - Similarity: cosine
//
// Bu indexler, eski tek "embedding" alanı yerine multimodal yapıyı destekler.
// database.js içindeki normal createIndex çağrılarıyla değil, Atlas Search & Vector Search ekranından oluşturulur.
//
// Not:
// - Local Mongo tarafında Vector Search yoktur.
// - Local ortamda yalnızca validator + normal index değişiklikleri uygulanır.
// - Duplicate kararında ana sinyal text_embedding, image_embedding ise yardımcı sinyaldir.
ensureCollection("source_records", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "raw_document_id",
        "source_id",
        "canonical_url",
        "title",
        "body",
        "published_at",
        "category_predicted",
        "district_predicted",
        "location_text_extracted",
        "geocode_status",
        "pipeline_status",
        "record_status",
        "schema_version",
        "created_at",
        "updated_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        raw_document_id: { bsonType: "objectId" },
        source_id: { bsonType: "objectId" },
        canonical_url: { bsonType: "string", pattern: "^https?://" },
        title: { bsonType: "string" },
        body: { bsonType: "string" },
        summary: { bsonType: "string" },
        published_at: { bsonType: "date" },
        detected_language: { bsonType: "string" },
        category_predicted: { enum: MANDATORY_CATEGORIES },
        category_confidence: {
          bsonType: ["double", "int", "decimal"],
          minimum: 0,
          maximum: 1,
        },
        category_model_version: { bsonType: "string" },
        district_predicted: { bsonType: ["string", "null"] },
        district_confidence: {
          bsonType: ["double", "int", "decimal"],
          minimum: 0,
          maximum: 1,
        },
        location_text_extracted: { bsonType: ["string", "null"] },
        geocode_status: {
          enum: ["pending", "resolved", "failed", "approximate", "not_needed"],
        },
        geocode_provider: { bsonType: "string" },
        geocode_point: {
          bsonType: ["object", "null"],
          additionalProperties: false,
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: {
              bsonType: "array",
              minItems: 2,
              maxItems: 2,
              items: { bsonType: ["double", "int", "long", "decimal"] },
            },
          },
        },
        geocode_bbox: {
          bsonType: ["array", "null"],
          minItems: 4,
          maxItems: 4,
          items: { bsonType: ["double", "int", "long", "decimal"] },
        },
        text_hash: { bsonType: "string" },
        source_name_snapshot: { bsonType: "string" },
        source_url_snapshot: { bsonType: "string", pattern: "^https?://" },
        text_embedding: {
          bsonType: ["array","null"],
          items: { bsonType: ["double", "int", "long", "decimal"] },
          description:
            "Text embedding vector (multimodal duplicate detection için ana sinyal)",
        },
        text_embedding_model: {
          bsonType: ["string", "null"],
          description: "Text embedding model name",
        },
        text_embedding_dim: {
          bsonType: ["int", "long","null"],
          description: "Text embedding vector dimension",
        },

        image_embedding: {
          bsonType: ["array", "null"],
          items: { bsonType: ["double", "int", "long", "decimal"] },
          description: "Image embedding vector (opsiyonel yardımcı sinyal)",
        },
        image_embedding_model: {
          bsonType: ["string", "null"],
          description: "Image embedding model name",
        },
        image_embedding_dim: {
          bsonType: ["int", "long", "null"],
          description: "Image embedding vector dimension",
        },

        duplicate_status: {
          enum: ["pending", "unique", "duplicate", "skipped", "error"],
          description: "Duplicate detection workflow durumu",
        },
        duplicate_source_record_id: {
          bsonType: ["objectId", "null"],
          description: "Duplicate eşleşen source_records._id referansı",
        },
        duplicate_text_similarity: {
          bsonType: ["double", "int", "decimal", "null"],
          minimum: 0,
          maximum: 1,
          description: "Text embedding similarity skoru",
        },
        duplicate_image_similarity: {
          bsonType: ["double", "int", "decimal", "null"],
          minimum: 0,
          maximum: 1,
          description: "Image embedding similarity skoru",
        },
        duplicate_final_score: {
          bsonType: ["double", "int", "decimal", "null"],
          minimum: 0,
          maximum: 1,
          description: "Final duplicate score",
        },
        duplicate_threshold: {
          bsonType: ["double", "int", "decimal", "null"],
          minimum: 0,
          maximum: 1,
          description: "Duplicate karar eşiği",
        },
        duplicate_reason: {
          bsonType: ["string", "null"],
          description: "Duplicate karar gerekçesi",
        },

        kaynak_listesi: {
          bsonType: ["array","null"],
          items: { bsonType: "string" },
          description:
            "Birleştirilen veya eşleşen haber kaynaklarının domain listesi",
        },
        pipeline_status: {
          enum: [
            "ingested",
            "normalized",
            "classified",
            "geocoded",
            "embedded",
            "clustered",
            "served",
            "failed",
          ],
        },
        record_status: { enum: ["active", "hidden", "deleted", "review"] },
        pipeline_run_id: { bsonType: "string" },
        schema_version: { bsonType: "string" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex(
  "source_records",
  { raw_document_id: 1 },
  { name: "raw_document_id_unique", unique: true },
);
ensureIndex(
  "source_records",
  { canonical_url: 1 },
  { name: "source_record_url" },
);
ensureIndex(
  "source_records",
  { source_id: 1, published_at: -1 },
  { name: "source_published_at" },
);
ensureIndex(
  "source_records",
  { category_predicted: 1, district_predicted: 1, published_at: -1 },
  { name: "category_district_published_at" },
);
ensureIndex(
  "source_records",
  { geocode_point: "2dsphere" },
  { name: "geocode_point_2dsphere", sparse: true },
);
ensureIndex("source_records", { text_hash: 1 }, { name: "text_hash" });
ensureIndex(
  "source_records",
  { duplicate_status: 1, published_at: -1 },
  { name: "duplicate_status_published_at" },
);

ensureIndex(
  "source_records",
  { duplicate_source_record_id: 1 },
  { name: "duplicate_source_record_id", sparse: true },
);

ensureIndex(
  "source_records",
  { duplicate_final_score: -1 },
  { name: "duplicate_final_score", sparse: true },
);

ensureIndex(
  "source_records",
  { kaynak_listesi: 1 },
  { name: "kaynak_listesi", sparse: true },
);

// 5) EVENTS
ensureCollection("events", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "event_type",
        "title_canonical",
        "summary_canonical",
        "status",
        "is_active",
        "district",
        "primary_location_text",
        "centroid",
        "time_start",
        "latest_published_at",
        "source_count",
        "record_count",
        "sources_summary",
        "schema_version",
        "created_at",
        "updated_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        event_type: { enum: MANDATORY_CATEGORIES },
        title_canonical: { bsonType: "string" },
        summary_canonical: { bsonType: "string" },
        description_canonical: { bsonType: "string" },
        status: {
          enum: ["open", "resolved", "monitoring", "archived", "review"],
        },
        is_active: { bsonType: "bool" },
        district: { bsonType: "string" },
        primary_location_text: { bsonType: "string" },
        centroid: {
          bsonType: "object",
          additionalProperties: false,
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: {
              bsonType: "array",
              minItems: 2,
              maxItems: 2,
              items: { bsonType: ["double", "int", "long", "decimal"] },
            },
          },
        },
        time_start: { bsonType: "date" },
        latest_published_at: { bsonType: "date" },
        source_count: { bsonType: ["int", "long"], minimum: 1 },
        record_count: { bsonType: ["int", "long"], minimum: 1 },
        sources_summary: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            additionalProperties: false,
            required: ["source_name", "source_url", "published_at"],
            properties: {
              source_name: { bsonType: "string" },
              source_url: { bsonType: "string", pattern: "^https?://" },
              published_at: { bsonType: "date" },
            },
          },
        },
        schema_version: { bsonType: "string" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex(
  "events",
  { event_type: 1, latest_published_at: -1 },
  { name: "event_type_latest_published_at" },
);
ensureIndex(
  "events",
  { district: 1, latest_published_at: -1 },
  { name: "district_latest_published_at" },
);
ensureIndex(
  "events",
  { is_active: 1, latest_published_at: -1 },
  { name: "active_latest_published_at" },
);
ensureIndex(
  "events",
  { centroid: "2dsphere" },
  { name: "centroid_2dsphere", sparse: true },
);

// 6) EVENT_RECORDS
ensureCollection("event_records", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "event_id",
        "source_record_id",
        "match_score",
        "match_reason",
        "is_primary",
        "dedup_version",
        "model_version",
        "cluster_run_id",
        "created_at",
        "updated_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        event_id: { bsonType: "objectId" },
        source_record_id: { bsonType: "objectId" },
        match_score: {
          bsonType: ["double", "int", "decimal"],
          minimum: 0,
          maximum: 1,
        },
        match_reason: {
          enum: [
            "hash_exact",
            "embedding_90_plus",
            "title_similarity",
            "manual_review",
            "multimodal_duplicate_threshold",
          ],
        },
        is_primary: { bsonType: "bool" },
        dedup_version: { bsonType: "string" },
        model_version: { bsonType: "string" },
        cluster_run_id: { bsonType: "string" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex(
  "event_records",
  { source_record_id: 1 },
  { name: "source_record_id_unique", unique: true },
);
ensureIndex("event_records", { event_id: 1 }, { name: "event_id" });
ensureIndex(
  "event_records",
  { event_id: 1, is_primary: 1 },
  {
    name: "one_primary_per_event",
    unique: true,
    partialFilterExpression: { is_primary: true },
  },
);

// 7) GEOCODING_CACHE
ensureCollection("geocoding_cache", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "_id",
        "normalized_query",
        "provider",
        "status",
        "result_quality",
        "created_at",
        "expires_at",
      ],
      properties: {
        _id: { bsonType: "string" },
        normalized_query: { bsonType: "string" },
        provider: { enum: ["nominatim", "pelias", "manual"] },
        status: { enum: ["hit", "miss", "failed", "ambiguous"] },
        result_quality: {
          enum: ["exact", "approximate", "district", "city", "none"],
        },
        result_point: {
          bsonType: ["object", "null"],
          additionalProperties: false,
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: {
              bsonType: "array",
              minItems: 2,
              maxItems: 2,
              items: { bsonType: ["double", "int", "long", "decimal"] },
            },
          },
        },
        result_bbox: {
          bsonType: ["array", "null"],
          minItems: 4,
          maxItems: 4,
          items: { bsonType: ["double", "int", "long", "decimal"] },
        },
        district: { bsonType: "string" },
        city: { bsonType: "string" },
        country: { bsonType: "string" },
        confidence: {
          bsonType: ["double", "int", "decimal"],
          minimum: 0,
          maximum: 1,
        },
        raw_response_path: { bsonType: "string" },
        created_at: { bsonType: "date" },
        expires_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex(
  "geocoding_cache",
  { expires_at: 1 },
  { name: "ttl_expires_at", expireAfterSeconds: 0 },
);
ensureIndex(
  "geocoding_cache",
  { result_point: "2dsphere" },
  { name: "result_point_2dsphere", sparse: true },
);
ensureIndex(
  "geocoding_cache",
  { provider: 1, normalized_query: 1 },
  { name: "provider_query" },
);

// 8) REVIEW_QUEUE (minimal)
ensureCollection("review_queue", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      additionalProperties: false,
      required: [
        "entity_type",
        "entity_object_id",
        "reason",
        "status",
        "created_at",
      ],
      properties: {
        _id: { bsonType: "objectId" },
        entity_type: { enum: ["source_record", "event"] },
        entity_object_id: { bsonType: "objectId" },
        reason: { bsonType: "string" },
        status: { enum: ["open", "resolved", "ignored"] },
        resolution_note: { bsonType: "string" },
        resolver: { bsonType: "string" },
        resolved_at: { bsonType: "date" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

ensureIndex(
  "review_queue",
  { status: 1, created_at: -1 },
  { name: "status_created_at" },
);

// Seed mandatory sources
[
  {
    domain: "cagdaskocaeli.com.tr",
    display_name: "Çağdaş Kocaeli",
    base_url: "https://www.cagdaskocaeli.com.tr",
    scraper_type: "static",
  },
  {
    domain: "ozgurkocaeli.com.tr",
    display_name: "Özgür Kocaeli",
    base_url: "https://www.ozgurkocaeli.com.tr",
    scraper_type: "static",
  },
  {
    domain: "seskocaeli.com",
    display_name: "Ses Kocaeli",
    base_url: "https://www.seskocaeli.com",
    scraper_type: "dynamic",
  },
  {
    domain: "yenikocaeli.com",
    display_name: "Yeni Kocaeli",
    base_url: "https://www.yenikocaeli.com",
    scraper_type: "static",
  },
  {
    domain: "bizimyaka.com",
    display_name: "Bizim Yaka Kocaeli",
    base_url: "https://www.bizimyaka.com",
    scraper_type: "dynamic",
  },
].forEach(function (src) {
  db.sources.updateOne(
    { domain: src.domain },
    {
      $setOnInsert: {
        domain: src.domain,
        display_name: src.display_name,
        base_url: src.base_url,
        scraper_type: src.scraper_type,
        region: "Kocaeli",
        language: "tr",
        local_source: true,
        active: true,
        created_at: new Date(),
        updated_at: new Date(),
      },
    },
    { upsert: true },
  );
});

// Startup check
const activeDomains = db.sources
  .find({ active: true }, { domain: 1, _id: 0 })
  .toArray()
  .map(function (x) {
    return x.domain;
  });
const missing = SOURCE_WHITELIST.filter(function (d) {
  return activeDomains.indexOf(d) === -1;
});
if (missing.length > 0) {
  throw new Error("Missing mandatory domains: " + missing.join(", "));
}

print("Multimodal source_records schema initialized successfully.");
