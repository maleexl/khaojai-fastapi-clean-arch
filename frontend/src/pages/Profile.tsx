import { useAuth } from '../contexts/AuthContext';

export default function Profile() {
  const { user, refreshUser } = useAuth();

  if (!user) {
    return (
      <div className="text-center py-8 text-gray-500">
        Loading profile...
        <button onClick={refreshUser} className="block mx-auto mt-2 text-blue-600 hover:underline">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto bg-white p-8 rounded-lg shadow">
      <h1 className="text-2xl font-bold mb-6">Profile</h1>
      <dl className="space-y-3">
        <div>
          <dt className="text-sm text-gray-500">User ID</dt>
          <dd className="font-mono text-sm">{user.id}</dd>
        </div>
        <div>
          <dt className="text-sm text-gray-500">Email</dt>
          <dd data-testid="profile-email">{user.email}</dd>
        </div>
        <div>
          <dt className="text-sm text-gray-500">Username</dt>
          <dd data-testid="profile-username" className="font-semibold">{user.username}</dd>
        </div>
        <div>
          <dt className="text-sm text-gray-500">Status</dt>
          <dd>
            <span className={user.is_active ? 'text-green-600' : 'text-red-600'}>
              {user.is_active ? 'Active' : 'Inactive'}
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-sm text-gray-500">Created</dt>
          <dd className="text-sm">{new Date(user.created_at).toLocaleString()}</dd>
        </div>
      </dl>
    </div>
  );
}
