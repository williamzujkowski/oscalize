# System Security Plan (SSP)
## Example Cloud Service SSP

### System Identification

**System Name:** Example Cloud Service  
**System Type:** Software as a Service (SaaS)  
**System ID:** ECS-001  
**FIPS-199 Level:** Moderate  

### System Characteristics

**System Description:**
This is an example cloud-based software service that provides document management capabilities to federal agencies. The system is hosted on AWS infrastructure and follows FedRAMP security controls.

**System Boundaries:**
The system boundary includes:
- Web application frontend
- API gateway
- Database servers
- Load balancers
- Authentication services

**Security Categorization (FIPS-199):**
- **Confidentiality:** Moderate
- **Integrity:** Moderate  
- **Availability:** Low

### Control Implementations

#### AC-1 Access Control Policy and Procedures

**Implementation Status:** Implemented

**Control Implementation:**
The organization has implemented comprehensive access control policies and procedures. All user access is managed through centrally managed identity providers with multi-factor authentication required for all administrative access.

**Responsible Role:** Security Team, System Administrator

**Assessment Procedures:**
- Review access control policies annually
- Test authentication mechanisms quarterly
- Audit user access logs monthly

#### AC-2 Account Management

**Implementation Status:** Implemented

**Control Implementation:**
User accounts are managed through automated provisioning systems. Account creation, modification, and deletion are logged and monitored. Privileged accounts require additional approval workflows.

**Responsible Role:** Identity Management Team

#### AU-1 Audit and Accountability Policy and Procedures

**Implementation Status:** Implemented

**Control Implementation:**
Comprehensive audit logging is implemented across all system components. Logs are centrally collected, monitored, and retained for compliance requirements.

#### IA-2 Identification and Authentication (Organizational Users)

**Implementation Status:** Implemented

**Control Implementation:**
All users must authenticate using multi-factor authentication (MFA). Authentication integrates with organizational identity providers supporting SAML 2.0 and OpenID Connect.

### System Components

#### Web Application Tier
- **Component Type:** Software
- **Deployment:** AWS ECS containers
- **Criticality:** High

#### Database Tier  
- **Component Type:** Database
- **Deployment:** AWS RDS PostgreSQL
- **Encryption:** At rest and in transit
- **Criticality:** High

#### Authentication Service
- **Component Type:** Service
- **Provider:** AWS Cognito
- **Integration:** SAML/OIDC
- **Criticality:** Critical

### Appendices

This SSP references the following attachments:
- A-1: System Architecture Diagrams
- A-2: Network Security Architecture  
- A-3: Data Flow Diagrams
- A-4: FedRAMP Customer Responsibility Matrix
- A-5: Integrated Inventory Workbook
- A-6: Plan of Actions and Milestones (POA&M)