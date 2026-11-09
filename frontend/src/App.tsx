
import { useState, type FormEvent } from 'react'
import './App.css'

type LoginResponse = {
  access_token: string
  token_type: string
}

function App() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isLoading) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username.trim(),
          password,
        }),
      })

      if (response.status === 401) {
        setError('Usuário ou senha incorretos.')
        return
      }

      if (!response.ok) {
        setError('Não foi possível realizar o login. Tente novamente.')
        return
      }

      const data: LoginResponse = await response.json()

      if (!data.access_token || data.token_type.toLowerCase() !== 'bearer') {
        setError('Resposta de autenticação inválida.')
        return
      }

      setAccessToken(data.access_token)
      setPassword('')
    } catch {
      setError(
        'Não foi possível conectar ao servidor. Verifique se o sistema está em execução.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  if (accessToken) {
    return (
      <main className="login-page">
        <section className="login-card" aria-labelledby="welcome-title">
          <header className="login-header">
            <img
              src="/kids-logo.jpeg"
              alt="Church City Kids"
              className="login-logo"
            />

            <h1 id="welcome-title">Bem-vindo ao Ministério Kids</h1>
            <p>Login realizado com sucesso!</p>
          </header>

          <button
            type="button"
            className="login-button"
            onClick={() => {
              setAccessToken(null)
              setUsername('')
              setPassword('')
              setError(null)
            }}
          >
            Sair
          </button>

          <footer className="login-footer">
            Church City Arapiraca
          </footer>
        </section>
      </main>
    )
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <header className="login-header">
          <img
            src="/kids-logo.jpeg"
            alt="Church City Kids"
            className="login-logo"
          />

          <h1 id="login-title">Bem-vindo ao Ministério Kids</h1>
          <p>Entre para iniciar a recepção das crianças.</p>
        </header>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="username">Usuário</label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              placeholder="Digite seu usuário"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="Digite sua senha"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          {error && (
            <p role="alert" className="login-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={isLoading}
          >
            {isLoading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <footer className="login-footer">
          Church City Arapiraca
        </footer>
      </section>
    </main>
  )
}

export default App
