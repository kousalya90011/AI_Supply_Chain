import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";

function Layout({ auth, onLogout }) {
  return (
    <div className="app-layout">
      <Sidebar auth={auth} />

      <div className="main-area">
        <Header auth={auth} onLogout={onLogout} />

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
