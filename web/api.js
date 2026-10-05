// Cookie sessions stay on the server; this file contains no keys or tokens.
window.api = (() => {
  async function request(path, body) {
    const response = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
      headers: body === undefined ? {} : {'Content-Type':'application/json','X-Little-Steps':'1'},
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Please try again');
    return data;
  }
  async function result(fn) {
    try { return {data: await fn(), error: null}; }
    catch (error) { return {data: null, error}; }
  }
  return {
    get: path => request(path),
    rpc: (name, args) => result(() => request('/api/rpc/'+encodeURIComponent(name),args)),
    auth: {
      signInAsGuest: () => result(() => request('/api/auth/guest',{})),
      getUser: () => result(() => request('/api/auth/me')),
      signInWithPassword: credentials => result(() => request('/api/auth/login',credentials)),
      signUp: ({email,password}) => result(() => request('/api/auth/register',{email,password})),
      signOut: () => result(() => request('/api/auth/logout',{}))
    }
  };
})();
