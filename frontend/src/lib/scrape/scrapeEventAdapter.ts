import type {
  RawScrapeEvent,
  ScrapeLogDetail,
  ScrapeLogEntry,
  ScrapeLogTone,
} from "@/lib/scrape/types";

const eventTitles: Record<string, string> = {
  job_submitted: "Is kuyruga alindi",
  job_started: "Scrape basladi",
  job_heartbeat: "Scrape suruyor",
  job_cancelling: "Durdurma istendi",
  job_cancelled: "Scrape durduruldu",
  job_retrying: "Yeniden deneme planlandi",
  job_failed: "Scrape hata verdi",
  job_completed: "Scrape tamamlandi",
  job_partial: "Scrape kismi tamamlandi",
  job_stale_ack: "Eski is kaydi temizlendi",
  dataset_reset: "Bootstrap oncesi temizlik",
  workspace_reset_manual: "Veritabani temizlendi",
  refresh_preserving_active_dataset: "Aktif veri korunuyor",
  refresh_generation_started: "Yeni dataset hazirlaniyor",
  source_crawl_started: "Kaynak basladi",
  source_listing_collected: "Liste toplandi",
  source_progress_checkpoint: "URL'ler isleniyor",
  source_crawl_completed: "Kaynak tamamlandi",
  source_crawl_failed: "Kaynak hata verdi",
  source_crawl_skipped: "Kaynak atlandi",
  crawl_summary_completed: "Kaynak turu bitti",
  refresh_cutover_started: "Cutover basladi",
  refresh_cleanup_completed: "Yeni veri aktive edildi",
  refresh_cleanup_skipped: "Aday veri atildi",
  refresh_cleanup_failed: "Cutover hata verdi",
  scheduler_job_skipped: "Zaten kuyruktaydi",
  scheduler_submit_failed: "Scheduler isi gonderemedi",
};

const reasonLabels: Record<string, string> = {
  skipped_by_config: "Konfigurasyon geregi atlandi",
  unsupported_source: "Desteklenmeyen kaynak",
  lease_not_acquired: "Lease alinamadi",
  no_active_sources: "Aktif kaynak yok",
  no_refresh_eligible_sources: "Refresh icin uygun kaynak kalmadi",
  refresh_skipped_sources_present: "Beklenmeyen skip olustu",
  refresh_source_count_mismatch: "Kaynak sayisi uyusmuyor",
  refresh_session_count_mismatch: "Session sayisi uyusmuyor",
  refresh_not_fully_successful: "Tum kaynaklar basariyla bitmedi",
};

const outcomeLabels: Record<string, string> = {
  inserted: "Yeni haber yazildi",
  duplicate_merged: "Tekrar haber mevcut kayda birlestirildi",
  lookback_filtered: "Lookback filtresi nedeniyle atlandi",
  invalid_record: "Baslik veya icerik eksik oldugu icin atlandi",
  source_processing_error: "URL islenirken hata olustu",
};

function getTone(event: RawScrapeEvent): ScrapeLogTone {
  if (event.event === "job_partial") {
    return "warning";
  }
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
    return value ? "evet" : "hayir";
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

function buildProgressLabel(current: unknown, total: unknown): string | null {
  const currentValue = toShortValue(current);
  const totalValue = toShortValue(total);

  if (!currentValue || !totalValue) {
    return null;
  }

  return `${currentValue} / ${totalValue}`;
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

function buildSourceProgressDetails(
  details: ScrapeLogDetail[],
  rawDetails: Record<string, unknown>,
  outcomeCode: string | null,
): void {
  const progress = buildProgressLabel(rawDetails.url_index, rawDetails.total_urls);
  if (progress) {
    details.push({ label: "Ilerleme", value: progress });
  }

  pushDetail(details, "Toplam URL", rawDetails.total_urls ?? rawDetails.listing_count);

  const outcome = outcomeCode ? outcomeLabels[outcomeCode] ?? outcomeCode : null;
  if (outcomeCode === "source_processing_error") {
    if (outcome) {
      details.push({ label: "Durum", value: outcome });
    }
    pushDetail(details, "Hata", rawDetails.error ?? rawDetails.error_message);
  }
}

function buildSourceCompletedDetails(
  details: ScrapeLogDetail[],
  rawDetails: Record<string, unknown>,
): void {
  pushDetail(details, "Toplam URL", rawDetails.listing_count);
  pushDetail(details, "Yeni kayit", rawDetails.inserted_count);
  pushDetail(details, "Tekrar", rawDetails.duplicate_count);
  pushDetail(details, "Disarida kalan", rawDetails.lookback_filtered_count);
  pushDetail(details, "Hata", rawDetails.failed_count);
}

function buildCrawlSummaryDetails(
  details: ScrapeLogDetail[],
  rawDetails: Record<string, unknown>,
): void {
  pushDetail(details, "Aktif kaynak", rawDetails.active_sources);
  pushDetail(details, "Islenen kaynak", rawDetails.processed_sources);
  pushDetail(details, "Hata veren", rawDetails.failed_sources);
  pushDetail(details, "Atlanan", rawDetails.skipped_sources);
}

function buildDetails(event: RawScrapeEvent): ScrapeLogDetail[] {
  const details: ScrapeLogDetail[] = [];
  const rawDetails =
    event.details && typeof event.details === "object" ? event.details : {};
  const outcomeCode =
    typeof rawDetails.outcome === "string" && rawDetails.outcome.trim()
      ? rawDetails.outcome
      : null;

  if (event.event === "source_progress_checkpoint") {
    buildSourceProgressDetails(details, rawDetails, outcomeCode);
    return details;
  }

  if (event.event === "source_listing_collected") {
    pushDetail(details, "Toplam URL", rawDetails.listing_count);
    return details;
  }

  if (
    event.event === "source_crawl_completed" ||
    event.event === "source_crawl_failed" ||
    event.event === "source_crawl_skipped"
  ) {
    pushDetail(details, "Kaynak", rawDetails.display_name ?? event.source);
    pushDetail(details, "Session", rawDetails.session_id);
    buildSourceCompletedDetails(details, rawDetails);
    pushDetail(details, "Hata turu", rawDetails.error_type);
    pushDetail(details, "Hata", rawDetails.error ?? rawDetails.error_message);
    return details;
  }

  if (event.event === "crawl_summary_completed") {
    buildCrawlSummaryDetails(details, rawDetails);
    return details;
  }

  if (
    event.event === "job_completed" ||
    event.event === "job_partial" ||
    event.event === "job_failed" ||
    event.event === "job_cancelling" ||
    event.event === "job_cancelled"
  ) {
    pushDetail(details, "Sonuc", rawDetails.result_status);
    pushDetail(details, "Hata veren", rawDetails.failed_sources);
    pushDetail(details, "Islenen kaynak", rawDetails.processed_sources);
    pushDetail(details, "Hata", rawDetails.error ?? rawDetails.error_message);
    pushDetail(details, "Iptal istendi", rawDetails.cancel_requested);
    return details;
  }

  if (event.event === "workspace_reset_manual" || event.event === "dataset_reset") {
    pushDetail(details, "Toplam silinen", rawDetails.total_deleted);
    const deletedCounts = buildDeletedCounts(rawDetails.deleted_counts);
    if (deletedCounts) {
      details.push({ label: "Silinenler", value: deletedCounts });
    }
    return details;
  }

  pushDetail(details, "Kaynak", rawDetails.display_name ?? event.source);
  pushDetail(details, "Scraper", rawDetails.scraper_type);
  pushDetail(details, "Liste sayfasi", rawDetails.base_url);
  pushDetail(details, "Session", rawDetails.session_id);

  const progress = buildProgressLabel(rawDetails.url_index, rawDetails.total_urls);
  if (progress) {
    details.push({ label: "Ilerleme", value: progress });
  }

  const outcome = outcomeCode ? outcomeLabels[outcomeCode] ?? outcomeCode : null;
  if (outcome) {
    details.push({ label: "Sonuc", value: outcome });
  }

  pushDetail(details, "Islenen URL", rawDetails.current_url ?? rawDetails.sample_url);
  pushDetail(details, "Kayit basligi", rawDetails.record_title);
  pushDetail(details, "Bulunan URL", rawDetails.listing_count);
  pushDetail(details, "Maksimum URL", rawDetails.max_urls_per_source);
  pushDetail(details, "Detay cekilen", rawDetails.fetched_count);
  pushDetail(details, "Yazilan", rawDetails.parsed_count);
  pushDetail(details, "Yeni kayit", rawDetails.inserted_count);
  pushDetail(details, "Birlesen tekrar", rawDetails.duplicate_count);
  pushDetail(details, "Lookback disinda", rawDetails.lookback_filtered_count);
  pushDetail(details, "Hatali kayit", rawDetails.failed_count);
  pushDetail(details, "Aktif kaynak", rawDetails.active_sources);
  pushDetail(details, "Islenen kaynak", rawDetails.processed_sources);
  pushDetail(details, "Hata veren kaynak", rawDetails.failed_sources);
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
  pushDetail(details, "Hata turu", rawDetails.error_type);
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
    title: eventTitles[rawEvent.event] ?? "Scrape guncellemesi",
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
