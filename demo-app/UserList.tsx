export function UserList({ data }: { data: { items?: { name: string }[] } }) {
  const users = data?.items ?? [];
  return (
    <ul>
      {users.map((user) => (
        <li key={user.name}>{user.name}</li>
      ))}
    </ul>
  );
}
