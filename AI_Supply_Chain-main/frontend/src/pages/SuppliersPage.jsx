import { useEffect, useState } from "react";
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier } from "../api/suppliersApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function SuppliersPage({ auth }) {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [form, setForm] = useState({ supplier_id: "", name: "", region: "", tier: "", status: "ACTIVE" });

  const isAdmin = auth?.role === "ADMIN";
  const isManager = auth?.role === "SUPPLY_CHAIN_MANAGER";

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getSuppliers();
      setSuppliers(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load suppliers.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuppliers();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      setError("");
      setSuccessMsg("");
      await createSupplier(form);
      setForm({ supplier_id: "", name: "", region: "", tier: "", status: "ACTIVE" });
      setSuccessMsg("Supplier created successfully.");
      await loadSuppliers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create supplier.");
    }
  };

  const handleToggleStatus = async (supplier) => {
    try {
      setError("");
      setSuccessMsg("");
      const newStatus = supplier.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
      await updateSupplier(supplier.supplier_id, { status: newStatus });
      setSuccessMsg(`Supplier ${supplier.supplier_id} marked as ${newStatus}.`);
      await loadSuppliers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update supplier status.");
    }
  };

  const handleDelete = async (supplierId) => {
    try {
      setError("");
      setSuccessMsg("");
      await deleteSupplier(supplierId);
      setSuccessMsg(`Supplier ${supplierId} deleted.`);
      await loadSuppliers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete supplier.");
    }
  };

  if (loading) return <Loading message="Loading suppliers..." />;

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">SUPPLIER OPERATIONS</p>
          <h1>Suppliers</h1>
        </div>
      </section>

      {error && <ErrorMessage title="Suppliers error" message={error} onRetry={loadSuppliers} />}

      {successMsg && (
        <div className="system-card" style={{ marginBottom: "16px", borderColor: "rgba(34, 197, 94, 0.4)", background: "rgba(34, 197, 94, 0.08)" }}>
          <strong style={{ color: "#22c55e" }}>{successMsg}</strong>
        </div>
      )}

      {isAdmin && (
        <section className="investigation-card" style={{ marginBottom: "20px" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">MANAGE</span>
              <h2>Add supplier</h2>
            </div>
          </div>

          <form onSubmit={handleCreate} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
            <input className="search-input" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} placeholder="Supplier ID" required />
            <input className="search-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Name" required />
            <input className="search-input" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} placeholder="Region" required />
            <input className="search-input" value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })} placeholder="Tier" required />
            <select className="search-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>
            <button type="submit" className="primary-button">Create Supplier</button>
          </form>
        </section>
      )}

      <section className="data-table-wrapper">
        {suppliers.length === 0 ? (
          <EmptyState title="No suppliers" message="There are currently no suppliers found." />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>Supplier ID</th>
                <th>Name</th>
                <th>Region</th>
                <th>Tier</th>
                <th>Status</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.supplier_id}>
                  <td>{supplier.supplier_id}</td>
                  <td>{supplier.name}</td>
                  <td>{supplier.region}</td>
                  <td>{supplier.tier}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        backgroundColor: supplier.status === "ACTIVE" ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
                        color: supplier.status === "ACTIVE" ? "#22c55e" : "#ef4444",
                      }}
                    >
                      {supplier.status}
                    </span>
                  </td>
                  {isAdmin && (
                    <td>
                      <button className="secondary-button" style={{ marginRight: "8px" }} onClick={() => handleToggleStatus(supplier)}>Toggle</button>
                      <button className="secondary-button" onClick={() => handleDelete(supplier.supplier_id)}>Delete</button>
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

export default SuppliersPage;
