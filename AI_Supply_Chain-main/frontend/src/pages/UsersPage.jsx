import { useEffect, useState } from "react";
import { getUsers, createUser, updateUser, deleteUser } from "../api/usersApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function UsersPage({ auth }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [form, setForm] = useState({
    username: "",
    email: "",
    name: "",
    password: "",
    role: "SUPPLIER",
    supplier_id: "",
  });

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getUsers();
      setUsers(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      setError("");
      setSuccessMsg("");
      await createUser({
        ...form,
        supplier_id: form.supplier_id ? form.supplier_id.trim() : null,
      });
      setForm({ username: "", email: "", name: "", password: "", role: "SUPPLIER", supplier_id: "" });
      setSuccessMsg("User created successfully.");
      await loadUsers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create user.");
    }
  };

  const handleToggleStatus = async (user) => {
    try {
      setError("");
      setSuccessMsg("");
      const nextStatus = user.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
      await updateUser(user.id, { status: nextStatus });
      setSuccessMsg(`User ${user.username} status changed to ${nextStatus}.`);
      await loadUsers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update user status.");
    }
  };

  const handleDelete = async (userId) => {
    try {
      setError("");
      setSuccessMsg("");
      await deleteUser(userId);
      setSuccessMsg(`User #${userId} deleted.`);
      await loadUsers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete user.");
    }
  };

  if (loading) return <Loading message="Loading users..." />;

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">USER ADMINISTRATION</p>
          <h1>Users</h1>
        </div>
      </section>

      {error && <ErrorMessage title="Users error" message={error} onRetry={loadUsers} />}

      {successMsg && (
        <div className="system-card" style={{ marginBottom: "16px", borderColor: "rgba(34, 197, 94, 0.4)", background: "rgba(34, 197, 94, 0.08)" }}>
          <strong style={{ color: "#22c55e" }}>{successMsg}</strong>
        </div>
      )}

      <section className="investigation-card" style={{ marginBottom: "20px" }}>
        <div className="section-header">
          <div>
            <span className="section-eyebrow">CREATE USER</span>
            <h2>Add user</h2>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
          <input className="search-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="Username" required />
          <input className="search-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email" required />
          <input className="search-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Name" required />
          <input className="search-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Password" required />
          <select className="search-input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="ADMIN">ADMIN</option>
            <option value="SUPPLY_CHAIN_MANAGER">SUPPLY_CHAIN_MANAGER</option>
            <option value="SUPPLIER">SUPPLIER</option>
          </select>
          <input className="search-input" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} placeholder="Supplier ID (if Supplier)" />
          <button type="submit" className="primary-button">Create User</button>
        </form>
      </section>

      <section className="data-table-wrapper">
        {users.length === 0 ? (
          <EmptyState title="No users" message="There are currently no users found." />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Name</th>
                <th>Role</th>
                <th>Supplier ID</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>#{user.id}</td>
                  <td>{user.username}</td>
                  <td>{user.name || "-"}</td>
                  <td>{user.role}</td>
                  <td>{user.supplier_id || "-"}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        backgroundColor: user.status === "ACTIVE" ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
                        color: user.status === "ACTIVE" ? "#22c55e" : "#ef4444",
                      }}
                    >
                      {user.status || "ACTIVE"}
                    </span>
                  </td>
                  <td>
                    <button className="secondary-button" style={{ marginRight: "8px" }} onClick={() => handleToggleStatus(user)}>Toggle</button>
                    <button className="secondary-button" onClick={() => handleDelete(user.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default UsersPage;
