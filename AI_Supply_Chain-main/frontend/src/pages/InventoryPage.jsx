import { useEffect, useState } from "react";
import { getInventory, createInventory, deleteInventory } from "../api/inventoryApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function InventoryPage({ auth }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [form, setForm] = useState({ product_id: "", date: "", inventory_level: "", demand: "", stockout: false });

  const isAdmin = auth?.role === "ADMIN";
  const isAdminOrManager = auth?.role === "ADMIN" || auth?.role === "SUPPLY_CHAIN_MANAGER";

  const loadInventory = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getInventory();
      setRecords(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load inventory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventory();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      setError("");
      setSuccessMsg("");
      await createInventory({
        ...form,
        date: new Date(form.date).toISOString(),
        inventory_level: Number(form.inventory_level),
        demand: Number(form.demand),
      });
      setForm({ product_id: "", date: "", inventory_level: "", demand: "", stockout: false });
      setSuccessMsg("Inventory record created successfully.");
      await loadInventory();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create inventory record.");
    }
  };

  const handleDelete = async (inventoryId) => {
    try {
      setError("");
      setSuccessMsg("");
      await deleteInventory(inventoryId);
      setSuccessMsg(`Inventory record #${inventoryId} deleted.`);
      await loadInventory();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete inventory record.");
    }
  };

  if (loading) return <Loading message="Loading inventory..." />;

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">INVENTORY OPERATIONS</p>
          <h1>Inventory</h1>
        </div>
      </section>

      {error && <ErrorMessage title="Inventory error" message={error} onRetry={loadInventory} />}

      {successMsg && (
        <div className="success-banner">
          <span style={{ fontSize: "16px" }}>✓</span>
          <strong>{successMsg}</strong>
        </div>
      )}

      {isAdminOrManager && (
        <section className="investigation-card" style={{ marginBottom: "24px" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">MANAGE</span>
              <h2>Add inventory</h2>
            </div>
          </div>

          <form onSubmit={handleCreate} className="form-grid">
            <div className="form-field">
              <label>Product ID *</label>
              <input className="search-input" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} placeholder="e.g. P00001" required />
            </div>
            <div className="form-field">
              <label>Inventory Date *</label>
              <input className="search-input" type="datetime-local" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
            </div>
            <div className="form-field">
              <label>Inventory Level *</label>
              <input className="search-input" type="number" min="0" value={form.inventory_level} onChange={(e) => setForm({ ...form, inventory_level: e.target.value })} placeholder="e.g. 500" required />
            </div>
            <div className="form-field">
              <label>Demand Qty *</label>
              <input className="search-input" type="number" min="0" value={form.demand} onChange={(e) => setForm({ ...form, demand: e.target.value })} placeholder="e.g. 120" required />
            </div>
            <div className="form-field" style={{ justifyContent: "center" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "inherit", cursor: "pointer", height: "42px", margin: 0 }}>
                <input type="checkbox" checked={form.stockout} onChange={(e) => setForm({ ...form, stockout: e.target.checked })} style={{ width: "auto !important", minHeight: "auto" }} />
                Stockout Risk
              </label>
            </div>
            <div className="form-field" style={{ justifyContent: "flex-end" }}>
              <button type="submit" className="primary-button" style={{ height: "42px", width: "100%" }}>Create Inventory</button>
            </div>
          </form>
        </section>
      )}

      <section className="data-table-wrapper">
        {records.length === 0 ? (
          <EmptyState title="No inventory" message="There are currently no inventory records found." />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Product</th>
                <th>Date</th>
                <th>Level</th>
                <th>Demand</th>
                <th>Stockout</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>#{record.id}</td>
                  <td>{record.product_id}</td>
                  <td>{new Date(record.date).toLocaleDateString()}</td>
                  <td>{record.inventory_level}</td>
                  <td>{record.demand}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        backgroundColor: record.stockout ? "rgba(239, 68, 68, 0.15)" : "rgba(34, 197, 94, 0.15)",
                        color: record.stockout ? "#ef4444" : "#22c55e",
                      }}
                    >
                      {record.stockout ? "YES" : "NO"}
                    </span>
                  </td>
                  {isAdmin && (
                    <td>
                      <button className="secondary-button" onClick={() => handleDelete(record.id)}>Delete</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default InventoryPage;
