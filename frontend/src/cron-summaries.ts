export type PromptSummary = {
  purpose: string
  scope: string
  source: string
}

const source = 'Diringkas dari isi prompt/job snapshot Hermes; bukan dari nama job saja.'

export const promptSummaries: Record<string, PromptSummary> = {
  'audit-daily': { purpose: 'Melakukan audit operasional harian secara read-only dan menghasilkan laporan temuan.', scope: 'Proxmox PVE, OMV VM, seluruh LXC, Docker, aplikasi homelab, seluruh Hermes profile, project, storage, backup, dan SMART.', source },
  'audit-weekly': { purpose: 'Melakukan deep audit mingguan untuk mencari masalah struktural dan tren yang tidak cukup diperiksa oleh audit harian.', scope: 'Integritas 6 profile Hermes, skills, memory database, konfigurasi, cron, channel, SMART semua disk, pertumbuhan storage, umur backup, dan kesehatan project.', source },
  'homelab-daily-infra-map-only': { purpose: 'Melakukan pemetaan dan pemeriksaan infrastruktur homelab secara read-only, lalu menyusun evidence untuk review.', scope: 'Proxmox, VM/LXC, Docker, storage, Hermes ecosystem, dan project yang tercantum pada scope sysadmin.', source },
  'homelab-rolling-health-check': { purpose: 'Melakukan rolling health check sebagai pemeriksaan tambahan di antara audit infrastruktur harian.', scope: 'Live state homelab, service, Docker, storage, dan komponen platform-reliability; job ini melengkapi, bukan menggantikan, audit harian.', source },
  'hermes-daily-health-scan': { purpose: 'Memeriksa kesehatan harian homelab dan ekosistem Hermes tanpa melakukan remediation.', scope: 'Proxmox, OMV, LXC, service, profile Hermes, skills, cron, dan project penting.', source },
  'hermes-weekly-deep-audit': { purpose: 'Menjalankan audit penuh mingguan dengan fokus pada keamanan, integritas, dan tren.', scope: 'Infrastruktur, seluruh profile/skills/cron Hermes, storage, backup, project, serta referensi kontrol keamanan.', source },
  'code-health-check-weekly': { purpose: 'Menyusun laporan mingguan tentang kesehatan codebase dan workflow engineering.', scope: 'Rotasi skill health, delegated code patterns, pre-commit hygiene, architecture gaps, validasi shared lessons, dan laporan perubahan skill.', source },
  'daily-assistant-scan': { purpose: 'Menyusun daily report untuk assistant dengan membaca agenda dan sumber administrasi pribadi.', scope: 'Google Calendar rolling window dan sumber assistant lain yang tersedia; jika sumber timeout, menggunakan fallback window yang lebih pendek.', source },
  'weekly-researcher-investigation-queue': { purpose: 'Menyegarkan antrean investigasi researcher setiap minggu.', scope: 'Shared reports, knowledge inbox, validator output, temuan, peluang improvement, dan action queue.', source },
  'cron-health-watchdog': { purpose: 'Memantau kesehatan cron lintas profile dan hanya mengirim alert ketika ada masalah yang perlu perhatian.', scope: 'Status scheduler dan kategori health tier dari seluruh profile; sukses normal dibuat silent.', source },
  'scorecard-decline-watchdog': { purpose: 'Mendeteksi penurunan scorecard dan mengirim alert jika ambang MIS-4 terpenuhi.', scope: 'Specialist scorecards dan scorecard flagger; kondisi normal tidak mengirim pesan.', source },
  'knowledge-pipeline-daily': { purpose: 'Menjalankan pipeline knowledge harian untuk validasi dan promosi data.', scope: 'Knowledge pipeline stages validate dan promote; output normal dibuat silent.', source },
  'inbox-aging-watchdog': { purpose: 'Mendeteksi item knowledge inbox yang terlalu lama belum diproses.', scope: 'Umur item pada knowledge inbox dan alert ketika backlog melewati aturan watchdog.', source },
  'weekly-learning-review': { purpose: 'Menghasilkan laporan review pembelajaran mingguan dari evidence yang terkumpul.', scope: 'Weekly learning report Hermes/shared lessons dan output Discord yang sudah diformat.', source },
  'report-freshness-sync': { purpose: 'Memeriksa dan menyelaraskan freshness report serta specialist scorecard.', scope: 'Report freshness metadata dan specialist scorecards; kondisi normal dibuat silent.', source },
  'homelab-mirror-push': { purpose: 'Mencerminkan report atau map homelab baru ke repository Digital Twin.', scope: 'Report homelab baru pada shared area dan target repository hermes-digital-twin.', source },
  'ticket-discord-listener': { purpose: 'Membaca post ticket baru dari Discord, membuat atau menggunakan kembali thread ticket, lalu memulai executor profile pemilik.', scope: 'Post berawalan ISSUE, AUDIT, atau IMPROVEMENT pada channel ticketing.', source },
  'ticket-watchdog': { purpose: 'Mendeteksi ticket yang macet, melakukan eskalasi, dan menutup ticket hanya setelah fix, health pass, dan quiet period.', scope: 'State dan umur ticket; output normal dibuat silent.', source },
  'ticket-dispatcher': { purpose: 'Memulai executor Hermes profile yang memiliki ticket baru atau orphan ticket setelah intake.', scope: 'Ticket yang siap dispatch dan routing ke assigned profile.', source },
  'audit-discord-listener': { purpose: 'Membaca post AUDIT baru, membuat thread audit, dan menyimpan state ticket audit.', scope: 'Audit channel yang ditentukan; tidak melakukan pekerjaan jika tidak ada event baru.', source },
  'audit-watchdog': { purpose: 'Mendeteksi audit ticket yang macet, mengeskalasi pada percobaan ketiga, dan menutup setelah hasil, health pass, serta quiet period tersedia.', scope: 'Audit ticket state dan result evidence.', source },
  'improvement-discord-listener': { purpose: 'Membaca post IMPROVEMENT baru, membuat thread improvement, dan menyimpan state.', scope: 'Improvement channel yang ditentukan; tidak mengirim output ketika tidak ada event.', source },
  'improvement-watchdog': { purpose: 'Memantau improvement ticket yang macet, mengeskalasi, dan menutup setelah result serta health pass.', scope: 'Improvement ticket state, result, dan quiet period.', source },
  'audit-improvement-dispatcher': { purpose: 'Menjadi safety-net dispatcher untuk sistem ticket audit dan improvement.', scope: 'Memeriksa dan menjalankan routing dispatcher untuk kedua sistem pada setiap tick.', source },
  'shared-lessons-aging-watchdog': { purpose: 'Mendeteksi shared lesson lintas profile yang stale lebih dari batas waktu.', scope: 'Shared-lessons backlog; mengirim alert hanya ketika ambang stale entry tercapai.', source },
  'ticket-aggregate-summary-daily': { purpose: 'Purpose belum terdokumentasi pada prompt snapshot yang tersedia.', scope: 'Scope tidak dapat dipastikan tanpa isi prompt.', source },
  'ticket-heartbeat-alert': { purpose: 'Purpose belum terdokumentasi pada prompt snapshot yang tersedia.', scope: 'Scope tidak dapat dipastikan tanpa isi prompt.', source },
  'cellar-incident-2h-observation': { purpose: 'Mengumpulkan sampel observasi berkala untuk incident cellar dan melaporkan hasil setelah jumlah sampel selesai.', scope: 'Script observasi incident yang dikonfigurasi; tick normal dibuat silent.', source },
  'dt-profile-sync': { purpose: 'Menyinkronkan profile Digital Twin secara incremental dan memperbarui README profile.', scope: 'Profile Hermes pada workspace hermes-digital-twin.', source },
  'dt-shared-sync': { purpose: 'Menyinkronkan shared surface Digital Twin secara idempotent.', scope: 'Shared surface workspace hermes-digital-twin; perubahan kosong tidak menghasilkan output.', source },
  'dt-reports-sync': { purpose: 'Menyinkronkan seluruh report dari shared reports ke Digital Twin.', scope: 'Semua subdirectory ~/.hermes-shared/reports, bukan hanya report homelab.', source },
  'dt-docs-sync': { purpose: 'Menyinkronkan dokumen root dan README Digital Twin serta mendeteksi README yang hilang.', scope: 'CHANGELOG, ROADMAP, dokumen root, dan directory docs workspace Digital Twin.', source },
  'dt-hermes-backup': { purpose: 'Membuat salinan backup root Hermes dan shared Hermes ke Digital Twin.', scope: 'Hermes root dan seluruh shared surface pada workspace hermes-digital-twin.', source },
  'orchestrator-pre-reset-snapshot': { purpose: 'Memperbarui snapshot carry-over sebelum reset dan mencoba menyelesaikan item pending yang sudah dapat di-resolve.', scope: 'carry-over.json dan pending items resolvable; hasil dikirim ke origin.', source },
}
