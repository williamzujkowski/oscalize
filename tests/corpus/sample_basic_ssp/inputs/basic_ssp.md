# System Security Plan - Basic Test Case

## System Identification

**System Name:** Test System  
**System Type:** Software Application  
**System ID:** TEST-001  
**FIPS-199 Level:** Moderate  

## System Characteristics

**System Description:**
This is a basic test system for validating OSCAL conversion. The system provides minimal required elements to demonstrate proper SSP structure and NIST OSCAL v1.1.3 compliance.

**System Boundaries:**
The system boundary includes:
- Application server
- Database server
- Web interface

**Security Categorization (FIPS-199):**
- **Confidentiality:** Moderate
- **Integrity:** Moderate  
- **Availability:** Low

## Control Implementations

### AC-1 Access Control Policy and Procedures

**Implementation Status:** Implemented

**Control Implementation:**
The organization has implemented access control policies and procedures. All user access requires authentication and authorization through the centralized identity management system.

**Responsible Role:** Security Team

### AC-2 Account Management  

**Implementation Status:** Implemented

**Control Implementation:**
User accounts are managed through automated provisioning. Account lifecycle includes creation, modification, and deletion with appropriate logging and monitoring.

**Responsible Role:** Identity Management Team

### AU-1 Audit and Accountability Policy and Procedures

**Implementation Status:** Implemented  

**Control Implementation:**
Comprehensive audit logging is implemented. All security-relevant events are logged, monitored, and retained according to organizational policy.

### System Components

#### Application Server
- **Component Type:** Software
- **Deployment:** Virtual Machine
- **Criticality:** High

#### Database Server
- **Component Type:** Database
- **Deployment:** Virtual Machine  
- **Encryption:** At rest and in transit
- **Criticality:** High