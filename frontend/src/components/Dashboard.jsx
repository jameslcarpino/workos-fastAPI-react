import { useState, useEffect } from 'react';

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/dashboard', {
        credentials: 'include',
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      } else if (response.status === 401) {
        // Redirect to home if not authenticated
        window.location.href = '/';
      } else {
        setError('Failed to load dashboard data');
      }
    } catch (error) {
      console.error('Dashboard data fetch failed:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading dashboard...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  return (
    <div className="dashboard">
      <h2>Dashboard</h2>
      {dashboardData && (
        <div>
          <div className="user-info">
            <h3>User Information</h3>
            <p>Name: {dashboardData.user.first_name} {dashboardData.user.last_name}</p>
            <p>Email: {dashboardData.user.email}</p>
          </div>
          <div className="dashboard-stats">
            <h3>Dashboard Statistics</h3>
            <p>Last Login: {dashboardData.dashboard_data.last_login}</p>
            <p>Role: {dashboardData.dashboard_data.role}</p>
            <p>Permissions: {dashboardData.dashboard_data.permissions.join(', ')}</p>
            <p>User ID: {dashboardData.user.id}</p>
            <p>User Email: {dashboardData.user.email}</p>
            <p>User First Name: {dashboardData.user.first_name}</p>
            <p>User Last Name: {dashboardData.user.last_name}</p>
            <p>Organization ID: {dashboardData.user.organization_id}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard; 