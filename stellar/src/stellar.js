/**
 * Stellar SDK integration — calls the deployed Soroban IncidentAudit contract.
 * CONTRACT_ID is set after deployment to Stellar testnet.
 */
import * as StellarSdk from "@stellar/stellar-sdk";

export const CONTRACT_ID = process.env.REACT_APP_CONTRACT_ID || "";
export const NETWORK_PASSPHRASE = StellarSdk.Networks.TESTNET;
export const HORIZON_URL = "https://horizon-testnet.stellar.org";
export const RPC_URL = "https://soroban-testnet.stellar.org";

const server = new StellarSdk.SorobanRpc.Server(RPC_URL);

/**
 * Read the total number of incidents stored on-chain.
 */
export async function getIncidentCount() {
  if (!CONTRACT_ID) return 0;
  const contract = new StellarSdk.Contract(CONTRACT_ID);
  const account = await server.getAccount(
    process.env.REACT_APP_PUBLIC_KEY || ""
  );
  const tx = new StellarSdk.TransactionBuilder(account, {
    fee: "100",
    networkPassphrase: NETWORK_PASSPHRASE,
  })
    .addOperation(contract.call("get_count"))
    .setTimeout(30)
    .build();

  const result = await server.simulateTransaction(tx);
  if (StellarSdk.SorobanRpc.Api.isSimulationError(result)) {
    console.error("Simulation error:", result);
    return 0;
  }
  const value = StellarSdk.scValToNative(result.result.retval);
  return Number(value);
}

/**
 * Read a single incident record from the contract by incident_id.
 */
export async function getIncident(incidentId, sourcePublicKey) {
  if (!CONTRACT_ID || !sourcePublicKey) return null;
  const contract = new StellarSdk.Contract(CONTRACT_ID);
  const account = await server.getAccount(sourcePublicKey);
  const tx = new StellarSdk.TransactionBuilder(account, {
    fee: "100",
    networkPassphrase: NETWORK_PASSPHRASE,
  })
    .addOperation(
      contract.call(
        "get_incident",
        StellarSdk.nativeToScVal(incidentId, { type: "string" })
      )
    )
    .setTimeout(30)
    .build();

  const result = await server.simulateTransaction(tx);
  if (StellarSdk.SorobanRpc.Api.isSimulationError(result)) {
    return null;
  }
  return StellarSdk.scValToNative(result.result.retval);
}

/**
 * Submit a store_incident transaction signed with the user's secret key.
 */
export async function storeIncident(secretKey, incident) {
  const keypair = StellarSdk.Keypair.fromSecret(secretKey);
  const account = await server.getAccount(keypair.publicKey());
  const contract = new StellarSdk.Contract(CONTRACT_ID);

  const tx = new StellarSdk.TransactionBuilder(account, {
    fee: "100",
    networkPassphrase: NETWORK_PASSPHRASE,
  })
    .addOperation(
      contract.call(
        "store_incident",
        StellarSdk.nativeToScVal(incident.incident_id, { type: "string" }),
        StellarSdk.nativeToScVal(incident.anomaly_type, { type: "string" }),
        StellarSdk.nativeToScVal(incident.severity, { type: "string" }),
        StellarSdk.nativeToScVal(incident.namespace, { type: "string" }),
        StellarSdk.nativeToScVal(incident.affected_resource, { type: "string" }),
        StellarSdk.nativeToScVal(incident.action, { type: "string" }),
        StellarSdk.nativeToScVal(BigInt(incident.timestamp), { type: "u64" })
      )
    )
    .setTimeout(30)
    .build();

  const prepared = await server.prepareTransaction(tx);
  prepared.sign(keypair);
  const response = await server.sendTransaction(prepared);
  return response.hash;
}

export function explorerUrl(contractId) {
  return `https://stellar.expert/explorer/testnet/contract/${contractId}`;
}

export function txExplorerUrl(hash) {
  return `https://stellar.expert/explorer/testnet/tx/${hash}`;
}
