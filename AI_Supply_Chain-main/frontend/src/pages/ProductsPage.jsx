import { useEffect, useState } from "react";
import { getProducts, createProduct, updateProduct, deleteProduct } from "../api/productsApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function ProductsPage({ auth, mode }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [form, setForm] = useState({ product_id: "", name: "", category: "", unit_cost: "", status: "ACTIVE" });

  const isAdmin = auth?.role === "ADMIN";
  const isSupplier = auth?.role === "SUPPLIER" || mode === "supplier";

  const loadProducts = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getProducts();
      setProducts(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load products.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      setError("");
      setSuccessMsg("");
      await createProduct({ ...form, unit_cost: Number(form.unit_cost) });
      setForm({ product_id: "", name: "", category: "", unit_cost: "", status: "ACTIVE" });
      setSuccessMsg("Product created successfully.");
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create product.");
    }
  };

  const handleToggleStatus = async (product) => {
    try {
      setError("");
      setSuccessMsg("");
      const newStatus = product.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
      await updateProduct(product.product_id, { status: newStatus });
      setSuccessMsg(`Product ${product.product_id} marked as ${newStatus}.`);
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update product.");
    }
  };

  const handleDelete = async (productId) => {
    try {
      setError("");
      setSuccessMsg("");
      await deleteProduct(productId);
      setSuccessMsg(`Product ${productId} deleted.`);
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete product.");
    }
  };

  if (loading) return <Loading message="Loading products..." />;

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">PRODUCT PORTFOLIO</p>
          <h1>{isSupplier ? "My Products" : "Products"}</h1>
        </div>
      </section>

      {error && <ErrorMessage title="Products error" message={error} onRetry={loadProducts} />}

      {successMsg && (
        <div className="success-banner">
          <span style={{ fontSize: "16px" }}>✓</span>
          <strong>{successMsg}</strong>
        </div>
      )}

      {isAdmin && (
        <section className="investigation-card" style={{ marginBottom: "24px" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">MANAGE</span>
              <h2>Add product</h2>
            </div>
          </div>

          <form onSubmit={handleCreate} className="form-grid">
            <input className="search-input" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} placeholder="Product ID" required />
            <input className="search-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Name" required />
            <input className="search-input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Category" required />
            <input className="search-input" type="number" step="0.01" value={form.unit_cost} onChange={(e) => setForm({ ...form, unit_cost: e.target.value })} placeholder="Unit cost" required />
            <select className="search-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>
            <button type="submit" className="primary-button" style={{ height: "42px" }}>Create Product</button>
          </form>
        </section>
      )}

      <section className="data-table-wrapper">
        {products.length === 0 ? (
          <EmptyState title="No products" message={isSupplier ? "No products associated with your supplier account." : "There are currently no products found."} />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>Product ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Unit Cost</th>
                <th>Status</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.product_id}>
                  <td>{product.product_id}</td>
                  <td>{product.name}</td>
                  <td>{product.category}</td>
                  <td>${Number(product.unit_cost || 0).toFixed(2)}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        backgroundColor: product.status === "ACTIVE" ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
                        color: product.status === "ACTIVE" ? "#22c55e" : "#ef4444",
                      }}
                    >
                      {product.status}
                    </span>
                  </td>
                  {isAdmin && (
                    <td>
                      <button className="secondary-button" style={{ marginRight: "8px" }} onClick={() => handleToggleStatus(product)}>Toggle</button>
                      <button className="secondary-button" onClick={() => handleDelete(product.product_id)}>Delete</button>
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

export default ProductsPage;
