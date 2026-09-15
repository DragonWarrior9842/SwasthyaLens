export type ReportMediaType = 'application/pdf' | 'image/jpeg' | 'image/png'
export type ReportStatus = 'pending_upload' | 'uploading' | 'uploaded' | 'upload_failed' | 'deleting'
export type ReportErrorCategory = 'invalid_file' | 'file_too_large' | 'unsupported_file_type' | 'filename_invalid' | 'storage_unavailable' | 'metadata_unavailable' | 'upload_interrupted' | 'integrity_mismatch'

export interface Report {
  id: string
  original_filename: string
  media_type: ReportMediaType
  size_bytes: number
  status: ReportStatus
  created_at: string
  updated_at: string
  error_category: ReportErrorCategory | null
}

export interface ReportPage {
  reports: Report[]
  next_cursor: string | null
}

export interface ReportConfig {
  max_upload_bytes: number
  allowed_media_types: ReportMediaType[]
}

export interface ReportDeletion {
  report_id: string
  status: 'deleting' | 'deleted'
}
