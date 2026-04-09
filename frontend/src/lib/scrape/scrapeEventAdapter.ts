import type {
  RawScrapeEvent,
  ScrapeLogDetail,
  ScrapeLogEntry,
  ScrapeLogTone,
} from "@/lib/scrape/types";

const eventTitles: Record<string, string> = {
  job_submitted: "İş kuyruğa alındı",
  job_started: "Scrape başladı",
  job_heartbeat: "Scrape sürüyor",
  job_retrying: "Yeniden deneme planlandı",
  job_failed: "Scrape hata verdi",
  job_completed: "Scrape tamamlandı",
  job_stale_ack: "Eski iş kaydı temizlendi",
  dataset_reset: "Bootstrap öncesi temizlik",
  refresh_preserving_active_dataset: "Aktif veri korunuyor",
  refresh_generation_started: "Yeni dataset hazırlanıyor",
  source_crawl_started: "Kaynak başladı",
  source_listing_collected: "Liste toplandı",
  source_crawl_completed: "Kaynak tamamlandı",
  source_crawl_failed: "Kaynak hata verdi",
  source_crawl_skipped: "Kaynak atlandı",
  crawl_summary_completed: "Kaynak turu bitti",
  refresh_cutover_started: "Cutover başladı",
  refresh_cleanup_completed: "Yeni veri aktive edildi",
  refresh_cleanup_skipped: "Aday veri atıldı",
  refresh_cleanup_failed: "Cutover hata verdi",
  scheduler_job_skipped: "Zaten kuyruktaydı",
  scheduler_submit_failed: "Scheduler işi gönderemedi",
};

const reasonLabels: Record<string, string> = {
  skipped_by_config: "Konfigürasyon gereği atlandı",
  unsupported_source: "Desteklenmeyen kaynak",
  lease_not_acquired: "Lease alınamadı",
  no_active_sources: "Aktif kaynak yok",
  no_refresh_eligible_sources: "Refresh için uygun kaynak kalmadı",
  refresh_skipped_sources_present: "Beklenmeyen skip oluştu",
  refresh_source_count_mismatch: "Kaynak sayısı uyuşmuyor",
  refresh_session_count_mismatch: "Session sayısı uyuşmuyor",
  refresh_not_fully_successful: "Tüm kaynaklar başarıyla bitmedi",
};

function getTone(event: RawScrapeEvent): ScrapeLogTone {
  if (
    event.status === "failed" ||
    event.status === "error" ||
    event.event.includes("failed")
  ) {
    return "error";
  }
  if (event.status === "completed") {
    return "success";
  }
  if (event.status === "skipped" || event.event.includes("skipped")) {
    return "warning";
  }
  if (event.event.includes("heartbeat")) {
    return "muted";
  }
  return "info";
}

function formatTimestamp(timestamp?: number): string {
  if (timestamp == null || !Number.isFinite(timestamp)) {
    return "--:--:--";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp * 1000));
}

function buildMetadata(event: RawScrapeEvent): string[] {
  const metadata: string[] = [];

  if (event.source) {
    metadata.push(event.source);
  }

  if (event.trigger_type) {
    metadata.push(`tetik: ${event.trigger_type}`);
  }

  if (typeof event.attempt_count === "number" && event.attempt_count > 0) {
    metadata.push(`deneme: ${event.attempt_count + 1}`);
  }

  if (event.job_id) {
    metadata.push(`job: ${event.job_id.slice(0, 8)}`);
  }

  return metadata;
}

function toShortValue(value: unknown): string | null {
  if (value == null) {
    return null;
  }

  if (typeof value === "string") {
    const normalized = value.trim();
    return normalized || null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : null;
  }

  if (typeof value === "boolean") {
    return value ? "evet" : "hayır";
  }

  return null;
}

function buildDeletedCounts(value: unknown): string | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const parts = Object.entries(value as Record<string, unknown>)
    .map(([key, count]) => {
      const normalizedCount = toShortValue(count);
      return normalizedCount ? `${key}: ${normalizedCount}` : null;
    })
    .filter((part): part is string => Boolean(part));

  return parts.length > 0 ? parts.join(" | ") : null;
}

function pushDetail(
  details: ScrapeLogDetail[],
  label: string,
  value: unknown,
): void {
  const normalized = toShortValue(value);
  if (!normalized) {
    return;
  }

  details.push({ label, value: normalized });
}

function buildDetails(event: RawScrapeEvent): ScrapeLogDetail[] {
  const details: ScrapeLogDetail[] = [];
  const rawDetails =
    event.details && typeof event.details === "object" ? event.details : {};

  pushDetail(details, "Kaynak", rawDetails.display_name ?? event.source);
  pushDetail(details, "Bulunan URL", rawDetails.listing_count);
  pushDetail(details, "Detay çekilen", rawDetails.fetched_count);
  pushDetail(details, "Yazılan", rawDetails.parsed_count);
  pushDetail(details, "Yeni kayıt", rawDetails.inserted_count);
  pushDetail(details, "Birleşen tekrar", rawDetails.duplicate_count);
  pushDetail(details, "Lookback dışında", rawDetails.lookback_filtered_count);
  pushDetail(details, "Hatalı kayıt", rawDetails.failed_count);
  pushDetail(details, "Aktif kaynak", rawDetails.active_sources);
  pushDetail(details, "İşlenen kaynak", rawDetails.processed_sources);
  pushDetail(details, "Atlanan kaynak", rawDetails.skipped_sources);
  pushDetail(details, "Toplam silinen", rawDetails.total_deleted);

  const deletedCounts = buildDeletedCounts(rawDetails.deleted_counts);
  if (deletedCounts) {
    details.push({ label: "Silinenler", value: deletedCounts });
  }

  const reason =
    typeof rawDetails.reason === "string" && rawDetails.reason.trim()
      ? reasonLabels[rawDetails.reason] ?? rawDetails.reason
      : null;
  if (reason) {
    details.push({ label: "Neden", value: reason });
  }

  pushDetail(details, "Jenerasyon", rawDetails.generation);
  pushDetail(details, "Hata türü", rawDetails.error_type);
  pushDetail(details, "Hata", rawDetails.error ?? rawDetails.error_message);

  return details;
}

export function adaptScrapeEvent(
  rawEvent: RawScrapeEvent,
  id: string,
): ScrapeLogEntry {
  return {
    id,
    event: rawEvent.event,
    title: eventTitles[rawEvent.event] ?? "Scrape güncellemesi",
    message: rawEvent.message,
    timestampLabel: formatTimestamp(rawEvent.timestamp),
    tone: getTone(rawEvent),
    metadata: buildMetadata(rawEvent),
    details: buildDetails(rawEvent),
    jobId: rawEvent.job_id,
    source: rawEvent.source,
    triggerType: rawEvent.trigger_type,
    status: rawEvent.status,
  };
}
