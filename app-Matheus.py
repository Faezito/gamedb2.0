from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt as bc
import sqlite3 as sql
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'data', 'gamedb.db')

def conectDB():
    con = sql.connect(db_path)
    cur = con.cursor()
    return con, cur

def getUser(username):
    con, cur = conectDB()

    cur.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cur.fetchone()

    con.close()
    return user

def getGames(user_id):
    con, cur = conectDB()

    cur.execute('SELECT * FROM games WHERE user_id = ?', (user_id,))
    cur.execute('ORDER BY status')
    games = cur.fetchall()

    con.close()
    return games

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard", username=session["username"]))
    return render_template("login.html", route=request.endpoint)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        if not username or not password:
            flash('Preencha todos os campos!')

        user = getUser(username)

        if user:
            senha = user[4].encode('utf-8')
            if bc.checkpw(password, senha):
                session['username'] = username
                return redirect(url_for('dashboard', username=username))
            else:
                flash('Senha incorreta!')
                return '''
                        <script>
                            alert('Usuário ou senha incorretos!')
                            window.history.back()
                        </script>
                        '''
        else:
            flash('Inválido', 'error')
            return '''
                        <script>
                            alert('Usuário ou senha incorretos!')
                            window.history.back()
                        </script>
                        '''
    return redirect(url_for('dashboard', username=username, route=request.endpoint))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Desconectado com sucesso!')
    return redirect(url_for('index'))

@app.route('/user/<username>')
def dashboard(username):
    
    if 'username' not in session or session['username'] != username:
        flash('Você foi desconectado!', 'error')
        return redirect(url_for('index'))

    con, cur = conectDB()
    cur.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cur.fetchone()

    con.close()

    if user:
        username = user[1]
        user_id = user[0]
        lista_de_jogos = getGames(user_id)
        return render_template('dashboard.html', user=username, games=lista_de_jogos, route=request.endpoint)
    else:
        flash('Usuário não encontrado!', 'error')
        return redirect(url_for('index'))

@app.route('/registerGame', methods=['GET', 'POST'])
def registerGame():
    user = session.get('username')

    if not user:
        flash('Sessão expirada!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title =  request.form['title']
        plataforma =  request.form['plataforma']
        genero =  request.form['genero']
        nota =  request.form['nota']
        capa = request.form['capa']
        horas = request.form['horas']
        status = request.form['status']

        if not title or not plataforma or not genero or not nota:
            flash('Preencha todos os campos!')
            return redirect(url_for('registerGame'))
        
        con, cur = conectDB()
        cur.execute('SELECT id FROM users WHERE username = ?', (user,))
        result = cur.fetchone()

        if result:
            user_id = result[0]
            cur.execute(
                'INSERT INTO games (title, plataforma, genero, nota, user_id, capa, horas, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (title, plataforma, genero, nota, user_id, capa, horas, status)
            )
            con.commit()
            con.close()

            flash('Jogo registrado com sucesso!')
            return f'''
                <script>
                    alert('Jogo cadastrado com sucesso!')
                    window.location.href = '{url_for("dashboard", username=session.get("username"))}'
                </script>
                '''

    return render_template('registerGame.html', user=session.get('username'), route=request.endpoint)

@app.route('/newUser', methods=['GET', 'POST'])
def newUser():
    if request.method == 'POST':
        nome = request.form['nome']
        username = request.form['username']
        email = request.form['email']
        senha = request.form['senha'].encode('utf-8')

        if not nome or not username or not email or not senha:
            flash('Preencha todos os campos!')
            return redirect(url_for('newUser'))
        
        senha_encriptada = bc.hashpw(senha, bc.gensalt()).decode('utf-8')

        con, cur = conectDB()

        cur.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        resultado = cur.fetchone()

        if resultado:
            flash('Usuário ou e-mail já cadastrado.')
            con.close()
            return f'''
                    <script>
                        alert('Usuário ou e-mail já cadastrados.')
                        window.location.href = '{url_for("newUser")}'
                    </script>
                    '''
        cur.execute('INSERT INTO users (nome, username, email, senha) VALUES (?, ?, ?, ?)', 
                    (nome, username, email, senha_encriptada))
        con.commit()
        con.close()
        return f'''
                <script>
                    alert('Usuário cadastrado com sucesso!')
                    window.location.href = '{url_for("index")}'
                </script>
                '''
    else:
        return render_template('newUser.html')
    
@app.route('/deleteGame/<int:game_id>', methods=['POST'])
def deleteGame(game_id):
    if 'username' not in session:
        flash('Você precisa estar logado para deletar jogos.')
        return redirect(url_for('index'))

    user = session['username']

    con, cur = conectDB()

    cur.execute('SELECT user_id FROM games WHERE id = ?', (game_id,))
    result = cur.fetchone()

    if result:
        cur.execute('SELECT id FROM users WHERE username = ?', (user,))
        user_id = cur.fetchone()[0]

        if result[0] == user_id:
            cur.execute('DELETE FROM games WHERE id = ?', (game_id,))
            con.commit()
            con.close()
            flash('Jogo deletado com sucesso!')
            return redirect(url_for('dashboard', username=user))

        else:
            return '''
                <script>
                    alert('Não foi possível deletar o jogo!')
                </script>
                '''
    else:
        flash('Jogo não encontrado!')
        return '''
                <script>
                    alert('Jogo não encontrado!')
                </script>
                '''

@app.route('/editGame/<int:game_id>', methods=['GET', 'POST'])
def editGame(game_id):
    con, cur = conectDB()

    if request.method == 'POST':
        cur.execute('SELECT title, nota, horas, status FROM games WHERE id = ?', (game_id,))
        game_antes = cur.fetchone()

        if not game_antes:
            flash('Jogo não encontrado!')
            return redirect(url_for('dashboard', username=session.get('username')))

        new_title = request.form.get('title') or game_antes[0]
        new_nota = request.form.get('nota') or game_antes[1]
        new_horas = request.form.get('horas') or game_antes[2]
        new_status = request.form.get('status') or game_antes[3]

        cur.execute('''
        UPDATE games SET
                    title = ?,
                    nota = ?,
                    horas = ?,
                    status = ?
        WHERE id = ?
    ''', (new_title, new_nota, new_horas, new_status, game_id))
        
        con.commit()
        con.close()

        flash('Jogo atualizado com sucesso!')
        return f'''
                <script>
                    alert('Jogo editado com sucesso!')
                    window.location.href = '{url_for("dashboard", username=session.get("username"))}'
                </script>
                '''
    
    cur.execute('SELECT * FROM games WHERE id = ?',  (game_id,))
    game = cur.fetchone()
    con.close()

    if game:
        return render_template('editGame.html', game=game, route = request.endpoint)
    else:
        flash('Jogo não encontrado!')
        return redirect(url_for('dashboard', username=session.get('username')))
    

if __name__ == "__main__":
    app.run(debug=True)
