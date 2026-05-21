# Buddha Dental — FastAPI Route Reference

All routes are prefixed with `/api/v1`.  
Auth header: `Authorization: Bearer <access_token>`  
Tenant is resolved from the JWT `tenant_id` claim — no subdomain parsing needed in the route itself.

**Role legend:** `SA` = SuperAdmin · `A` = Admin · `D` = Doctor · `R` = Receptionist

---

## Phase 1 — Foundation: Auth, Tenants, Users

### Authentication — `/auth`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `POST` | `/auth/register-tenant` | Register new clinic + first admin user | Public |
| `POST` | `/auth/login` | Login, returns access + refresh tokens | Public |
| `POST` | `/auth/refresh` | Refresh access token using refresh token | Public |
| `POST` | `/auth/logout` | Revoke refresh token | Any |
| `POST` | `/auth/logout-all` | Revoke all sessions for current user | Any |
| `GET`  | `/auth/me` | Get current user profile | Any |
| `PUT`  | `/auth/me` | Update own profile (name, phone, notifications) | Any |
| `POST` | `/auth/change-password` | Change own password | Any |
| `POST` | `/auth/otp/send` | Send OTP to registered phone | Public |
| `POST` | `/auth/otp/verify` | Verify OTP, return tokens | Public |

**Request — `POST /auth/login`**
```json
{ "username": "drprabin", "password": "••••••••" }
```
**Response**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "uuid", "role": "DOCTOR", "full_name": "Dr. Prabin Shah" }
}
```

---

### Tenant Management — `/tenants` _(SuperAdmin only)_

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/tenants` | List all tenants (paginated) | SA |
| `POST`   | `/tenants` | Create tenant | SA |
| `GET`    | `/tenants/{tenant_id}` | Get tenant details | SA |
| `PUT`    | `/tenants/{tenant_id}` | Update tenant plan/status | SA |
| `DELETE` | `/tenants/{tenant_id}` | Soft-deactivate tenant | SA |
| `POST`   | `/tenants/{tenant_id}/activate` | Re-activate tenant | SA |
| `GET`    | `/tenants/{tenant_id}/stats` | Usage stats for tenant | SA |

---

### User Management — `/users`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/users` | List all users in tenant | A |
| `POST`   | `/users` | Create user (doctor / receptionist) | A |
| `GET`    | `/users/{user_id}` | Get user profile | A, D (own) |
| `PUT`    | `/users/{user_id}` | Update user | A |
| `DELETE` | `/users/{user_id}` | Deactivate user | A |
| `PUT`    | `/users/{user_id}/role` | Change role | A |
| `PUT`    | `/users/{user_id}/permissions` | Override module permissions | A |
| `GET`    | `/users/doctors` | List active doctors with specializations | A, R |
| `GET`    | `/users/doctors/{doctor_id}/schedule` | Doctor's availability slots | A, R |

---

### Feature Flags — `/admin/feature-flags`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/admin/feature-flags` | Get all flags for current tenant | A |
| `PUT`  | `/admin/feature-flags/{flag_key}` | Enable/disable a flag | A |

---

## Phase 2 — Core Clinical Modules

### Patients — `/patients`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/patients` | List patients (search, filter, paginate) | A, D, R |
| `POST`   | `/patients` | Register new patient | A, R |
| `GET`    | `/patients/{patient_id}` | Get full patient profile | A, D, R |
| `PUT`    | `/patients/{patient_id}` | Update patient info | A, R |
| `DELETE` | `/patients/{patient_id}` | Soft-delete (status = INACTIVE) | A |
| `GET`    | `/patients/search` | Search by name / phone / patient_code | A, D, R |
| `POST`   | `/patients/check-duplicate` | Check for duplicate before creating | A, R |
| `GET`    | `/patients/{patient_id}/summary` | Printable one-page patient summary | A, D, R |
| `GET`    | `/patients/{patient_id}/timeline` | Chronological visit timeline | A, D, R |
| `GET`    | `/patients/{patient_id}/family` | List linked family members | A, D, R |
| `POST`   | `/patients/{patient_id}/family` | Link family member to primary account | A, R |
| `DELETE` | `/patients/{patient_id}/family/{member_id}` | Unlink family member | A, R |

**Query params for `GET /patients`:** `?search=&status=&doctor_id=&page=&per_page=&sort_by=last_visit`

---

### Medical Records — `/patients/{patient_id}/record`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET` | `/patients/{patient_id}/record` | Get full medical record | A, D, R |
| `POST` | `/patients/{patient_id}/record` | Create record (auto-created on patient register) | A, R |
| `PUT` | `/patients/{patient_id}/record` | Update record (insurance, emergency contact) | A, D, R |
| `PUT` | `/patients/{patient_id}/record/assign-doctor` | Assign primary doctor | A |

---

### Appointments — `/appointments`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/appointments` | List appointments (date range, doctor, status) | A, D, R |
| `POST`   | `/appointments` | Book new appointment | A, R |
| `GET`    | `/appointments/{appointment_id}` | Get appointment detail | A, D, R |
| `PUT`    | `/appointments/{appointment_id}` | Update appointment | A, R |
| `DELETE` | `/appointments/{appointment_id}` | Cancel appointment | A, R |
| `POST`   | `/appointments/{appointment_id}/confirm` | Confirm booked appointment | A, R |
| `POST`   | `/appointments/{appointment_id}/start` | Mark as In-Progress | A, D, R |
| `POST`   | `/appointments/{appointment_id}/complete` | Mark as Completed | A, D, R |
| `POST`   | `/appointments/{appointment_id}/no-show` | Mark as No-Show | A, R |
| `POST`   | `/appointments/{appointment_id}/reschedule` | Reschedule with new date/doctor | A, R |
| `POST`   | `/appointments/{appointment_id}/follow-up` | Create follow-up appointment | A, D, R |
| `GET`    | `/appointments/today` | Today's appointments with queue status | A, D, R |
| `GET`    | `/appointments/available-slots` | Get open slots for a doctor on a date | A, R |
| `POST`   | `/appointments/walk-in` | Register walk-in and add to queue | A, R |
| `GET`    | `/patients/{patient_id}/appointments` | All appointments for a patient | A, D, R |

**Query params for `GET /appointments`:** `?date_from=&date_to=&doctor_id=&status=&type=&page=&per_page=`

---

### Queue Management — `/queue`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/queue/today` | Live queue for today (all doctors) | A, D, R |
| `GET`  | `/queue/today/{doctor_id}` | Live queue for specific doctor | A, D, R |
| `POST` | `/queue/{appointment_id}/call` | Call next patient to chair | A, D, R |
| `POST` | `/queue/{appointment_id}/skip` | Skip token, send to end | A, R |
| `GET`  | `/queue/estimated-wait` | Estimated wait time for a token | A, R |
| `GET`  | `/queue/display` | Public display endpoint (no auth, for TV screen) | Public |

---

### Diagnosis — `/appointments/{appointment_id}/diagnosis`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/appointments/{appointment_id}/diagnosis` | Get diagnosis for visit | A, D |
| `POST` | `/appointments/{appointment_id}/diagnosis` | Create diagnosis | D |
| `PUT`  | `/appointments/{appointment_id}/diagnosis/{diagnosis_id}` | Update diagnosis | D |
| `GET`  | `/patients/{patient_id}/diagnoses` | All diagnoses for a patient | A, D |

**Tooth chart field format in request body:**
```json
{
  "tooth_chart": {
    "11": { "status": "root_canal", "stage": 2, "notes": "Pulp removed" },
    "36": { "status": "extraction", "stage": null, "notes": "" }
  }
}
```

---

### Treatment Plans — `/treatment-plans`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/treatment-plans` | List plans (filter by patient, type, status) | A, D, R |
| `POST`   | `/treatment-plans` | Create treatment plan | D |
| `GET`    | `/treatment-plans/{plan_id}` | Get plan with all sessions | A, D, R |
| `PUT`    | `/treatment-plans/{plan_id}` | Update plan details | D |
| `POST`   | `/treatment-plans/{plan_id}/complete` | Mark plan as completed | D |
| `POST`   | `/treatment-plans/{plan_id}/pause` | Pause active plan | D |
| `GET`    | `/patients/{patient_id}/treatment-plans` | All plans for a patient | A, D, R |

### Treatment Sessions — `/treatment-plans/{plan_id}/sessions`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/treatment-plans/{plan_id}/sessions` | List all sessions in plan | A, D, R |
| `POST` | `/treatment-plans/{plan_id}/sessions` | Add session | D |
| `PUT`  | `/treatment-plans/{plan_id}/sessions/{session_id}` | Update session notes/status | D |
| `POST` | `/treatment-plans/{plan_id}/sessions/{session_id}/complete` | Mark session done + set next | D |

---

### Procedures — `/procedures`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/procedures` | List procedures (filter by patient, date) | A, D, R |
| `POST`   | `/procedures` | Log a procedure | D |
| `GET`    | `/procedures/{procedure_id}` | Get procedure detail | A, D, R |
| `PUT`    | `/procedures/{procedure_id}` | Update procedure | D |
| `DELETE` | `/procedures/{procedure_id}` | Delete procedure | A, D |
| `GET`    | `/patients/{patient_id}/procedures` | All procedures for patient | A, D, R |

---

### Prescriptions — `/prescriptions`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/prescriptions` | List prescriptions | A, D, R |
| `POST`   | `/prescriptions` | Create prescription | D |
| `GET`    | `/prescriptions/{prescription_id}` | Get prescription detail | A, D, R |
| `GET`    | `/prescriptions/{prescription_id}/pdf` | Download prescription PDF | A, D, R |
| `GET`    | `/patients/{patient_id}/prescriptions` | All prescriptions for patient | A, D, R |

---

### Documents & Files — `/documents`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/documents` | List documents (filter by patient, type) | A, D, R |
| `POST` | `/documents/upload-url` | Get presigned S3 upload URL | A, D, R |
| `POST` | `/documents` | Register document after S3 upload | A, D, R |
| `GET`  | `/documents/{document_id}` | Get document metadata | A, D, R |
| `GET`  | `/documents/{document_id}/download-url` | Get presigned S3 download URL | A, D, R |
| `DELETE` | `/documents/{document_id}` | Delete document | A, D |
| `GET`  | `/patients/{patient_id}/documents` | All documents for patient | A, D, R |
| `GET`  | `/patients/{patient_id}/xrays` | X-rays only (for viewer) | A, D, R |

---

## Phase 3 — Billing & Notifications

### Billing Catalog — `/billing-catalog`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/billing-catalog` | List all service items | A, D, R |
| `POST`   | `/billing-catalog` | Add service item | A |
| `GET`    | `/billing-catalog/{item_id}` | Get item detail | A, D, R |
| `PUT`    | `/billing-catalog/{item_id}` | Update item | A |
| `DELETE` | `/billing-catalog/{item_id}` | Deactivate item | A |

---

### Invoices — `/invoices`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/invoices` | List invoices (filter by status, date, patient) | A, R |
| `POST`   | `/invoices` | Create invoice for an appointment | A, R |
| `GET`    | `/invoices/{invoice_id}` | Get invoice with line items | A, R |
| `PUT`    | `/invoices/{invoice_id}` | Update draft invoice | A, R |
| `POST`   | `/invoices/{invoice_id}/issue` | Finalise and issue invoice | A, R |
| `POST`   | `/invoices/{invoice_id}/void` | Void invoice with reason | A |
| `GET`    | `/invoices/{invoice_id}/pdf` | Download invoice PDF | A, R |
| `GET`    | `/invoices/{invoice_id}/receipt` | Download receipt PDF | A, R |
| `POST`   | `/invoices/{invoice_id}/print` | Trigger receipt print job | A, R |
| `GET`    | `/patients/{patient_id}/invoices` | All invoices for patient | A, R |
| `GET`    | `/invoices/overdue` | List overdue invoices with aging brackets | A |

**Query params for `GET /invoices`:** `?status=&patient_id=&date_from=&date_to=&overdue=true&page=&per_page=`

---

### Invoice Items — `/invoices/{invoice_id}/items`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `POST`   | `/invoices/{invoice_id}/items` | Add line item | A, R |
| `PUT`    | `/invoices/{invoice_id}/items/{item_id}` | Update line item | A, R |
| `DELETE` | `/invoices/{invoice_id}/items/{item_id}` | Remove line item | A, R |

---

### Payments — `/payments`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/payments` | List payments (date range, mode, received_by) | A |
| `POST` | `/payments` | Record payment against invoice | A, R |
| `GET`  | `/payments/{payment_id}` | Get payment detail | A, R |
| `POST` | `/payments/{payment_id}/refund` | Record refund with reason | A |
| `GET`  | `/patients/{patient_id}/payments` | Payment history for patient | A, R |

---

### Discount Approvals — `/discount-approvals`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/discount-approvals` | List pending/resolved approvals | A |
| `POST` | `/discount-approvals` | Request discount approval | A, R |
| `POST` | `/discount-approvals/{approval_id}/approve` | Approve discount | A |
| `POST` | `/discount-approvals/{approval_id}/reject` | Reject discount | A |

---

### Notifications — `/notifications`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/notifications/logs` | Notification delivery log | A |
| `POST` | `/notifications/send` | Manually send SMS to patient | A, R |
| `POST` | `/notifications/test-sms` | Send test SMS to check provider config | A |
| `GET`  | `/notifications/logs/{patient_id}` | Notification history for patient | A, R |

> Automated notifications (reminders, birthdays, overdue alerts) are triggered by Celery — no API call needed. These endpoints are for manual sends and log viewing only.

---

## Phase 4 — Reports, Admin & Hardening

### Reports & Analytics — `/reports`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET` | `/reports/daily-revenue` | Total collections, by mode, per doctor | A |
| `GET` | `/reports/monthly-revenue` | Month-on-month revenue chart + YTD | A |
| `GET` | `/reports/doctor-performance` | Patients, procedures, revenue per doctor | A |
| `GET` | `/reports/patient-acquisition` | New vs returning patients trend | A |
| `GET` | `/reports/pending-dues` | Outstanding balances with aging (30/60/90d) | A |
| `GET` | `/reports/top-treatments` | Procedure frequency + revenue contribution | A |
| `GET` | `/reports/revenue-by-doctor` | Comparative revenue across doctors | A |
| `GET` | `/reports/revenue-by-treatment` | Revenue by procedure category | A |
| `GET` | `/reports/daily-patient-average` | Rolling avg patients per day/doctor/shift | A |
| `GET` | `/reports/no-show-rate` | No-show % trended over time | A |
| `GET` | `/reports/follow-up-conversion` | Follow-up reminder → confirmed appointment rate | A |
| `GET` | `/reports/peak-hours` | Hourly patient volume heatmap | A |
| `GET` | `/reports/daily-cash-report` | Daily cash summary for closing | A, R |
| `GET` | `/reports/export/{report_type}` | Download report as CSV/Excel | A |

**Common query params for all reports:** `?date_from=&date_to=&doctor_id=&format=json|csv`

---

### Admin Settings — `/admin`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/admin/settings` | Get clinic system settings | A |
| `PUT`  | `/admin/settings` | Update system settings | A |
| `GET`  | `/admin/clinic-profile` | Get clinic branding + contact info | A |
| `PUT`  | `/admin/clinic-profile` | Update clinic profile | A |
| `POST` | `/admin/clinic-profile/logo` | Upload clinic logo | A |
| `GET`  | `/admin/audit-logs` | Full audit log (user, action, timestamp) | A |
| `GET`  | `/admin/audit-logs/{user_id}` | Audit logs for specific user | A |
| `POST` | `/admin/backup/trigger` | Trigger manual backup | A |
| `GET`  | `/admin/backup/list` | List available backups | A |

**Query params for audit logs:** `?user_id=&action=&resource_type=&date_from=&date_to=&page=&per_page=`

---

## Phase 5 — SaaS Scaling (Post-Launch)

### Tenant Self-Service — `/onboarding`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `POST` | `/onboarding/signup` | Public self-service clinic signup | Public |
| `POST` | `/onboarding/verify-email` | Verify email after signup | Public |
| `GET`  | `/onboarding/check-slug` | Check slug availability | Public |

### Subscription & Billing — `/subscription`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`  | `/subscription` | Current plan + usage | A |
| `POST` | `/subscription/upgrade` | Upgrade plan (triggers payment) | A |
| `POST` | `/subscription/cancel` | Cancel subscription | A |
| `GET`  | `/subscription/invoices` | SaaS billing invoices | A |
| `GET`  | `/subscription/usage` | Usage metrics (SMS sent, storage used) | A |

### Webhooks — `/webhooks`

| Method | Route | Description | Roles |
|--------|-------|-------------|-------|
| `GET`    | `/webhooks` | List registered webhooks | A |
| `POST`   | `/webhooks` | Register new webhook endpoint | A |
| `DELETE` | `/webhooks/{webhook_id}` | Remove webhook | A |
| `POST`   | `/webhooks/{webhook_id}/test` | Send test payload | A |

> Supported webhook events: `appointment.created`, `appointment.completed`, `payment.received`, `invoice.issued`, `patient.registered`

---

## Standard Response Envelopes

### Success
```json
{
  "success": true,
  "data": { },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 143,
    "total_pages": 8
  }
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "PATIENT_NOT_FOUND",
    "message": "No patient found with the given ID",
    "details": {}
  }
}
```

### Validation Error (422)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "phone", "msg": "Phone number already exists for this clinic" }
    ]
  }
}
```

---

## HTTP Status Codes Used

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No content (delete) |
| `400` | Bad request / business rule violation |
| `401` | Missing or invalid token |
| `403` | Insufficient role / feature flag off |
| `404` | Resource not found |
| `409` | Conflict (duplicate phone, existing record) |
| `422` | Validation error |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

---

## Authentication Notes

Every protected route requires:
```
Authorization: Bearer <access_token>
```

The JWT payload carries:
```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "role": "DOCTOR",
  "plan": "PRO",
  "iat": 1716000000,
  "exp": 1716003600
}
```

Access token TTL: `15 minutes`  
Refresh token TTL: `7 days` (rotated on each refresh)

---

## Feature-Gated Routes

Routes that check `feature_flags` before executing:

| Flag Key | Gates |
|----------|-------|
| `sms_reminders` | All automated SMS sending |
| `recall_campaigns` | `/notifications/recall` trigger |
| `vat_invoices` | `is_vat_invoice` field on invoice create |
| `multi_doctor` | More than 1 doctor user account |
| `analytics_dashboard` | All `/reports/*` endpoints |
| `document_storage` | All `/documents/*` endpoints |
| `family_linking` | `POST /patients/{id}/family` |
| `discount_approval` | `/discount-approvals` endpoints |
| `webhooks` | All `/webhooks/*` endpoints |

If a flag is disabled for the tenant, the API returns:
```json
{ "code": "FEATURE_DISABLED", "message": "This feature is not available on your current plan." }
```
with HTTP `403`.
