# Access Matrix (Role-Based)

Source: derived from current Django view mixins/dispatch checks in the codebase.

Legend:
- C = Create
- R = Read (list/detail/view page)
- U = Update
- D = Delete
- RF = Read File (download/view file)
- `✓` = access allowed
- blank = no access

Roles:
- SA = Super Admin
- AD = Admin
- DR = Doctor
- PT = Patient
- ST = Staff
- LA = Lab Assistant
- PH = Pharmacist

| Module | Action | Type | SA | AD | DR | PT | ST | LA | PH |
|---|---|---|---|---|---|---|---|---|---|
| Users | Manage users (staff/lab/pharmacist) | C |  | ✓ |  |  |  |  |  |
| Users | Manage users (staff/lab/pharmacist) | R | ✓ | ✓ |  |  |  |  |  |
| Users | Manage users (staff/lab/pharmacist) | U | ✓ | ✓ |  |  |  |  |  |
| Users | Manage users (staff/lab/pharmacist) | D | ✓ | ✓ |  |  |  |  |  |
| Users | Own staff-portal profile | R | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| Users | Own staff-portal profile | U | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| Users | Password change (staff portal) | U | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| Users | Axes lock list/unlock | R | ✓ |  |  |  |  |  |  |
| Patients | Self profile create | C |  |  |  | ✓ |  |  |  |
| Patients | Self profile view | R |  |  |  | ✓ |  |  |  |
| Patients | Self profile edit/account/password | U |  |  |  | ✓ |  |  |  |
| Patients | Patient create (hospital-side) | C |  | ✓ |  |  | ✓ |  |  |
| Patients | Patient list/detail (hospital-side) | R | ✓ | ✓ |  |  | ✓ |  |  |
| Patients | Patient update (hospital-side) | U | ✓ | ✓ | ✓ |  | ✓ |  |  |
| Patients | Patient delete | D | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital | C | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital | R | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital | U | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital | D | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital admin accounts | C | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital admin accounts | R | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital admin accounts | U | ✓ |  |  |  |  |  |  |
| Hospitals | Hospital admin accounts | D | ✓ |  |  |  |  |  |  |
| Hospitals | Own hospital (admin panel) | R |  | ✓ |  |  |  |  |  |
| Hospitals | Own hospital (admin panel) | U |  | ✓ |  |  |  |  |  |
| Hospitals | Departments (admin hospital) | C |  | ✓ |  |  |  |  |  |
| Hospitals | Departments (admin hospital) | R |  | ✓ |  |  |  |  |  |
| Hospitals | Departments (admin hospital) | U |  | ✓ |  |  |  |  |  |
| Hospitals | Departments (admin hospital) | D |  | ✓ |  |  |  |  |  |
| Doctors | Doctor management (admin/super-admin) | C | ✓ | ✓ |  |  |  |  |  |
| Doctors | Doctor management (admin/super-admin) | R | ✓ | ✓ |  |  |  |  |  |
| Doctors | Doctor management (admin/super-admin) | U | ✓ | ✓ |  |  |  |  |  |
| Doctors | Doctor management (admin/super-admin) | D | ✓ | ✓ |  |  |  |  |  |
| Doctors | Own doctor profile | R |  |  | ✓ |  |  |  |  |
| Doctors | Own doctor profile | U |  |  | ✓ |  |  |  |  |
| Doctors | Own schedule | C |  |  | ✓ |  |  |  |  |
| Doctors | Own schedule | R |  |  | ✓ |  |  |  |  |
| Doctors | Own schedule | U |  |  | ✓ |  |  |  |  |
| Doctors | Own schedule | D |  |  | ✓ |  |  |  |  |
| Appointments | Patient booking and own appointments | C |  |  |  | ✓ |  |  |  |
| Appointments | Patient booking and own appointments | R |  |  |  | ✓ |  |  |  |
| Appointments | Patient booking and own appointments | U |  |  |  | ✓ |  |  |  |
| Appointments | Doctor own appointments | R |  |  | ✓ |  |  |  |  |
| Appointments | Doctor own appointments | U |  |  | ✓ |  |  |  |  |
| Appointments | Admin/staff managed appointments | C |  | ✓ |  |  | ✓ |  |  |
| Appointments | Admin/staff managed appointments | R |  | ✓ |  |  | ✓ |  |  |
| Appointments | Admin/staff managed appointments | U |  | ✓ |  |  | ✓ |  |  |
| Payments | Appointment payment screen/update | U | ✓ | ✓ |  | ✓ |  |  |  |
| Payments | Admin/staff payment management | R |  | ✓ |  |  | ✓ |  |  |
| Payments | Admin/staff payment management | U |  | ✓ |  |  | ✓ |  |  |
| Payments | Patient own payment list/status | R |  |  |  | ✓ |  |  |  |
| Payments | Patient own payment method/process | U |  |  |  | ✓ |  |  |  |
| Medical Reports | Doctor patient-scoped reports | C |  |  | ✓ |  |  |  |  |
| Medical Reports | Doctor patient-scoped reports | R |  |  | ✓ |  |  |  |  |
| Medical Reports | Doctor patient-scoped reports | U |  |  | ✓ |  |  |  |  |
| Medical Reports | Doctor report file access | RF |  |  | ✓ |  |  |  |  |
| Medical Reports | Admin/lab report management | C |  | ✓ |  |  |  | ✓ |  |
| Medical Reports | Admin/lab report management | R |  | ✓ |  |  |  | ✓ |  |
| Medical Reports | Admin/lab report management | U |  | ✓ |  |  |  | ✓ |  |
| Medical Reports | Admin/lab report management | D |  | ✓ |  |  |  | ✓ |  |
| Medical Reports | Admin report file access | RF | ✓ | ✓ |  |  |  |  |  |
| Medical Reports | Patient own reports | R |  |  |  | ✓ |  |  |  |
| Medical Reports | Patient report sharing | U |  |  |  | ✓ |  |  |  |
| Medical Reports | Patient report file access | RF |  |  |  | ✓ |  |  |  |
| Prescriptions | Patient own prescription detail | R |  |  |  | ✓ |  |  |  |
| Prescriptions | Doctor own prescription | C |  |  | ✓ |  |  |  |  |
| Prescriptions | Doctor own prescription | R |  |  | ✓ |  |  |  |  |
| Prescriptions | Doctor own prescription | U |  |  | ✓ |  |  |  |  |
| Prescriptions | Admin/super-admin prescription management | C | ✓ | ✓ |  |  |  |  |  |
| Prescriptions | Admin/super-admin prescription management | U | ✓ | ✓ |  |  |  |  |  |
| Prescriptions | Admin/super-admin prescription management | D | ✓ | ✓ |  |  |  |  |  |
| Prescriptions | Admin/pharmacist prescription list/detail | R |  | ✓ |  |  |  |  | ✓ |
| Logs | Audit logs | R | ✓ | ✓ |  |  |  |  |  |
| AI Search | Doctor search/list page | R | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## Notes

- This matrix reflects current code behavior (view mixins and explicit dispatch checks), including some intentional strictness where super admin is not included in certain admin/staff or admin/lab/pharmacist mixins.
- Public flows like registration, login, OTP request/verify/reset, and hospital registration are not role-restricted CRUD records, so they are excluded from the table.
