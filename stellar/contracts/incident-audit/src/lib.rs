#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, symbol_short, vec, Env, String, Vec, Map};

/// On-chain record of a K8sWhisperer incident.
#[contracttype]
#[derive(Clone)]
pub struct IncidentRecord {
    pub incident_id: String,
    pub anomaly_type: String,
    pub severity: String,
    pub namespace: String,
    pub affected_resource: String,
    pub action: String,
    pub timestamp: u64,
}

const INCIDENTS_KEY: &str = "INCIDENTS";
const COUNT_KEY: &str = "COUNT";

#[contract]
pub struct IncidentAuditContract;

#[contractimpl]
impl IncidentAuditContract {
    /// Store a new incident record on-chain.
    pub fn store_incident(
        env: Env,
        incident_id: String,
        anomaly_type: String,
        severity: String,
        namespace: String,
        affected_resource: String,
        action: String,
        timestamp: u64,
    ) -> u32 {
        let record = IncidentRecord {
            incident_id: incident_id.clone(),
            anomaly_type,
            severity,
            namespace,
            affected_resource,
            action,
            timestamp,
        };

        // Store the record keyed by incident_id
        env.storage()
            .persistent()
            .set(&incident_id, &record);

        // Increment and return the count
        let count: u32 = env.storage().persistent().get(&symbol_short!("COUNT")).unwrap_or(0);
        let new_count = count + 1;
        env.storage().persistent().set(&symbol_short!("COUNT"), &new_count);

        new_count
    }

    /// Retrieve a specific incident by ID.
    pub fn get_incident(env: Env, incident_id: String) -> Option<IncidentRecord> {
        env.storage().persistent().get(&incident_id)
    }

    /// Get total number of incidents stored.
    pub fn get_count(env: Env) -> u32 {
        env.storage().persistent().get(&symbol_short!("COUNT")).unwrap_or(0)
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use soroban_sdk::Env;

    #[test]
    fn test_store_and_retrieve() {
        let env = Env::default();
        let contract_id = env.register_contract(None, IncidentAuditContract);
        let client = IncidentAuditContractClient::new(&env, &contract_id);

        let id = String::from_str(&env, "inc-001");
        let count = client.store_incident(
            &id,
            &String::from_str(&env, "CrashLoopBackOff"),
            &String::from_str(&env, "HIGH"),
            &String::from_str(&env, "production"),
            &String::from_str(&env, "api-pod-xyz"),
            &String::from_str(&env, "restart_pod"),
            &1704067200u64,
        );
        assert_eq!(count, 1);

        let record = client.get_incident(&id).unwrap();
        assert_eq!(record.severity, String::from_str(&env, "HIGH"));
    }
}
