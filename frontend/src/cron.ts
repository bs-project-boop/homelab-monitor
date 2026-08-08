import { promptSummaries } from './cron-summaries'
import type { Resource } from './api'

export type SchedulerClass = 'hermes_profile' | 'system_scheduler' | 'docker_worker' | 'hermes_unresolved' | 'other_scheduler'

export function classifyScheduler(resource: Resource, resources: Resource[]): SchedulerClass {
  if (resource.kind !== 'cron_job') return 'other_scheduler'
  const parent = resource.parent_id ? resources.find((candidate) => candidate.id === resource.parent_id) : null
  const owner = parent?.parent_id ? resources.find((candidate) => candidate.id === parent.parent_id) : null
  if (resource.source === 'hermes' && parent?.kind === 'cron_profile' && owner?.kind === 'hermes_profile') return 'hermes_profile'
  if (resource.source === 'hermes') return 'hermes_unresolved'
  if (['systemd', 'cron', 'proxmox'].includes(resource.source)) return 'system_scheduler'
  if (resource.source === 'docker' && resource.metadata.worker_type === 'docker_worker') return 'docker_worker'
  return 'other_scheduler'
}

export type CronExplanation = {
  owner: string
  ownerDetail: string
  purpose: string
  purposeBasis: string
  why: string
  ifFails: string
  executor: string
  target: string
  delivery: string
  schedule: string
  state: string
}

function text(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key]
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function profileName(job: Resource, resources: Resource[]): string | null {
  const cronProfile = job.parent_id ? resources.find((resource) => resource.id === job.parent_id) : null
  const owner = cronProfile?.parent_id ? resources.find((resource) => resource.id === cronProfile.parent_id) : null
  if (owner?.kind === 'hermes_profile' && owner.name) return owner.name.replace(/\s+profile$/i, '')
  return null
}

function purposeFor(name: string, metadata: Record<string, unknown>): { purpose: string; why: string; ifFails: string; basis: string } {
  const source = `${name} ${text(metadata, 'script') ?? ''} ${text(metadata, 'skills') ?? ''}`.toLowerCase()
  if (source.includes('watchdog') || source.includes('health')) return { purpose: 'Memeriksa kesehatan sistem atau job lain secara berkala dan memberi tanda ketika ada masalah.', why: 'Supaya masalah bisa diketahui sebelum menjadi gangguan yang lebih besar.', ifFails: 'Pemantauan dan peringatan dari job ini bisa terlambat; workload yang dipantau tidak otomatis diperbaiki oleh job ini.', basis: 'Disimpulkan dari nama/metadata job yang mengandung health atau watchdog.' }
  if (source.includes('audit')) return { purpose: 'Melakukan pemeriksaan/audit berkala terhadap konfigurasi, aktivitas, atau hasil kerja yang dipantau.', why: 'Supaya penyimpangan dan masalah operasional terlihat dalam laporan audit.', ifFails: 'Audit terbaru tidak terbuat atau terlambat, sehingga perubahan/masalah bisa tidak segera terlihat.', basis: 'Disimpulkan dari nama/metadata job yang mengandung audit.' }
  if (source.includes('backup')) return { purpose: 'Menjalankan atau memeriksa proses backup pada target yang ditentukan.', why: 'Supaya data dan konfigurasi memiliki salinan atau bukti backup yang dapat diperiksa.', ifFails: 'Backup atau verifikasi backup bisa tertunda; job ini tidak menghapus atau memulihkan data secara otomatis.', basis: 'Disimpulkan dari nama/workdir/metadata job yang mengandung backup.' }
  if (source.includes('sync') || source.includes('mirror')) return { purpose: 'Menyinkronkan data, laporan, atau artefak antar lokasi kerja yang tercatat.', why: 'Supaya salinan data tetap mengikuti sumbernya.', ifFails: 'Salinan tujuan bisa tertinggal dari sumber sampai sinkronisasi berikutnya berhasil.', basis: 'Disimpulkan dari nama/workdir job yang mengandung sync atau mirror.' }
  if (source.includes('report')) return { purpose: 'Menyusun atau memperbarui laporan dari data yang sudah tersedia.', why: 'Supaya hasil observasi dapat dibaca dan ditinjau secara berkala.', ifFails: 'Laporan terbaru tidak tersedia atau masih menggunakan data lama.', basis: 'Disimpulkan dari nama job yang mengandung report.' }
  if (source.includes('listener') || source.includes('dispatcher')) return { purpose: 'Menerima event atau meneruskan hasil event ke tujuan delivery yang ditentukan.', why: 'Supaya notifikasi atau alur kerja lanjutan tetap berjalan.', ifFails: 'Event/notifikasi yang masuk selama periode gagal dapat terlambat diproses; tidak ada retry yang diasumsikan di UI.', basis: 'Disimpulkan dari nama/mode job.' }
  if (source.includes('code') || source.includes('skill')) return { purpose: 'Menjalankan pemeriksaan atau pekerjaan terjadwal yang berkaitan dengan codebase dan skill Hermes.', why: 'Supaya pemeriksaan kualitas dan pengetahuan operasional tetap diperbarui.', ifFails: 'Hasil pemeriksaan atau sinkronisasi pengetahuan bisa tertunda.', basis: 'Disimpulkan dari nama dan metadata skills.' }
  if (source.includes('homelab')) return { purpose: 'Memperbarui atau memeriksa informasi operasional homelab secara berkala.', why: 'Supaya informasi inventory dan kesehatan tetap tersedia untuk review.', ifFails: 'Snapshot atau pemeriksaan homelab menjadi lebih lama; job ini bersifat observasi.', basis: 'Disimpulkan dari nama job dan metadata skills.' }
  return { purpose: 'Tujuan spesifik belum memiliki deskripsi eksplisit pada metadata collector; yang diketahui hanya job ini terdaftar sebagai tugas terjadwal.', why: 'Tujuan spesifik belum dapat dipastikan dari data aman yang tersedia.', ifFails: 'Tugas ini bisa terlambat atau tidak berjalan; dampak spesifik belum dapat dipastikan dari data collector.', basis: 'Tidak ada purpose eksplisit; hanya metadata scheduler yang tersedia.' }
}

function humanSchedule(schedule: string | null): string {
  if (!schedule) return 'Jadwal tidak tersedia'
  const known: Record<string, string> = { '0 8 * * *': 'Setiap hari pukul 08:00', '0 8 * * 1': 'Setiap Senin pukul 08:00', '0 0 * * *': 'Setiap hari tengah malam', '*/30 * * * *': 'Setiap 30 menit', '*/15 * * * *': 'Setiap 15 menit', '*/2 * * * *': 'Setiap 2 menit', '0 */6 * * *': 'Setiap 6 jam', '30 */6 * * *': 'Menit ke-30 setiap 6 jam' }
  return known[schedule] ?? `Jadwal scheduler: ${schedule}`
}

export function explainCron(job: Resource, resources: Resource[]): CronExplanation {
  const metadata = job.metadata
  const owner = profileName(job, resources)
  const purpose = purposeFor(job.name, metadata)
  const documented = promptSummaries[job.name]
  const backendPurpose = text(metadata, 'purpose')
  const backendScope = Array.isArray(metadata.scope) ? metadata.scope.filter((item): item is string => typeof item === 'string').join(', ') : ''
  const effectivePurpose = backendPurpose ?? documented?.purpose ?? purpose.purpose
  const effectiveWhy = backendScope ? `Scope pekerjaan: ${backendScope}.` : documented ? `Scope pekerjaan: ${documented.scope}` : purpose.why
  const effectiveBasis = backendPurpose ? `Ringkasan dari collector Hermes (${text(metadata, 'summary_source') ?? 'source job'}).` : documented?.source ?? purpose.basis
  const mode = text(metadata, 'mode')
  const skills = text(metadata, 'skills')
  const script = text(metadata, 'script')
  const workdir = text(metadata, 'workdir')
  const delivery = text(metadata, 'deliver')
  const target = workdir ? `Workspace ${workdir.split('/').filter(Boolean).slice(-2).join('/')}` : script ? `Script terdaftar ${script}` : delivery === 'local' ? 'Output lokal profile' : delivery === 'origin' ? 'Percakapan asal' : 'Target kerja tidak dijelaskan'
  const executor = job.source === 'hermes' ? mode?.startsWith('no-agent') ? 'Hermes scheduler menjalankan script terdaftar' : `Hermes profile${skills ? ` dengan skills: ${skills}` : ' menjalankan agent job'}` : `${job.source} scheduler pada parent resource`
  return { owner: owner ? `Hermes profile ${owner}` : job.source === 'hermes' ? 'Hermes profile tidak teridentifikasi' : `${job.source} scheduler`, ownerDetail: owner ? 'Profile ini memiliki dan mengatur cron tersebut.' : 'Owner spesifik belum tersedia pada metadata collector.', purpose: effectivePurpose, purposeBasis: effectiveBasis, why: effectiveWhy, ifFails: documented ? 'Jika job gagal, scope tersebut tidak diperiksa/disinkronkan pada jadwal ini. Tidak ada auto-remediation yang diasumsikan.' : purpose.ifFails, executor, target, delivery: delivery ? `Hasil dikirim ke ${delivery.startsWith('discord:') ? 'Discord (channel terdaftar)' : delivery}` : 'Delivery tidak ditentukan', schedule: humanSchedule(text(metadata, 'schedule')), state: text(metadata, 'state') ?? job.status }
}
