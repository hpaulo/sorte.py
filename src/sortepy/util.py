# encoding=utf8

import cookielib
import errno
import os
import sqlite3
import urllib2
import time


def get_config_path(app='sortepy'):
    """Obtém o caminho de configuração de acordo com o SO

    Por enquanto é suportado os sistemas POSIX e Windows (NT)
    """
    # Linux, UNIX, BSD, ...
    if os.name == 'posix':
        prefixo = '.config/'
        profile_dir = os.environ.get("HOME")

    # Windows 2000, XP, Vista, 7, 8, ...
    elif os.name == 'nt':
        prefixo = ''
        profile_dir = os.environ.get("APPDATA")

    # Se nenhum SO suportado foi detectado, lança uma exceção
    else:
        raise NotImplementedError("Caminho de configuração não detectado")

    return os.path.join(profile_dir, prefixo + app)


def makedirs(caminho):
    """Versão própria do makedirs()

    Essa versão não lança exceção se o caminho já existir
    """
    try:
        os.makedirs(caminho)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


class Util:
    def __init__(self, cfg_path=None):
        # Se o caminho é uma string vazia, não deve ser usado nenhum cache
        # Definido para propósitos de teste
        if cfg_path == '':
            self.in_cache = False
            return

        # Se nenhum caminho foi passado, usa diretório de configuração padrão
        if cfg_path is None:
            try:
                cfg_path = get_config_path()
            # Pode ocorrer de não conseguir definir o diretório para cfg_path
            except NotImplementedError:
                self.in_cache = False
                return

        # Cria diretórios de configuração, se não existirem
        cache_path = os.path.join(cfg_path, 'cache')
        makedirs(cache_path)

        # Define atributos de configuração
        self.pages_db = FileDB.open(os.path.join(cache_path, 'paginas.db'))
        self.temp_db = FileDB.open(os.path.join(cache_path, 'paginas-temp.db'))
        self.in_cache = True

    def download(self, url, in_cache=None):
        in_cache = in_cache if isinstance(in_cache, bool) else self.in_cache

        # Obtém a página do cache
        conteudo = None
        if in_cache:
            conteudo = self.cache(url)

        # Ou faz o download
        if conteudo is None:
            # As páginas de resultado de loterias exigem cookies
            cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            # A adição desse cookie dobra o tempo de resposta
            opener.addheaders.append(("Cookie", "security=true"))

            page = opener.open(url)
            conteudo = page.read()

            charset = page.headers.getparam('charset')
            if charset is not None:
                try:
                    conteudo = unicode(conteudo, charset)
                except (UnicodeDecodeError, LookupError):
                    pass

            if in_cache:
                self.cache(url, conteudo)

        return conteudo

    def cache(self, url, conteudo=None):
        # Sem conteúdo: leitura do cache
        if conteudo is None:
            try:
                return self.pages_db[url]
            except KeyError:
                valor = self.temp_db.get(url)
                if valor:
                    timestamp, conteudo = valor.split('|', 1)
                    if time.time() <= int(timestamp) + 1800:
                        return conteudo
                    else:
                        del self.temp_db[url]
                return None

        # Do contrário: escrita no cache
        else:
            self.pages_db[url] = conteudo

    def cache_evict(self, url):
        if self.in_cache and url in self.pages_db:
            self.temp_db[url] = "%d|" % int(time.time()) + self.pages_db[url]
            del self.pages_db[url]


class FileDB:
    @staticmethod
    def open(filename):
        db = FileDB._SQLite3(filename)
        return db

    class _SQLite3(object):
        __version__ = 0  # por enquanto não serve para nada

        def __init__(self, filename):
            self._conn = sqlite3.connect(filename)
            self._cur = self._conn.cursor()
            self._create_schema()

        def close(self):
            self._conn.commit()
            self._conn.close()

        def flush(self):
            self._conn.commit()

        def __del__(self):
            try:
                self.close()
            except sqlite3.ProgrammingError:
                pass

        def _create_schema(self):
            cursor = self._cur
            try:
                cursor.execute("CREATE TABLE map (key PRIMARY KEY, value)")
                self._write_dbversion(self.__version__)
            # caso a tabela 'map' já exista
            except sqlite3.OperationalError:
                pass

        def _read_dbversion(self):
            cursor = self._cur
            (dbversion,) = cursor.execute('PRAGMA user_version').fetchone()
            return dbversion

        def _write_dbversion(self, version):
            cursor = self._cur
            cursor.execute('PRAGMA user_version = %d' % version)

        def get(self, key, default=None):
            try:
                return self[key]
            except KeyError:
                return default

        def __setitem__(self, key, value):
            cursor = self._cur
            try:
                cursor.execute("INSERT INTO map VALUES (?, ?)", (key, value))
            except sqlite3.IntegrityError:
                cursor.execute("UPDATE map SET value=? WHERE key=?",
                               (value, key))

        def __getitem__(self, key):
            cursor = self._cur
            cursor.execute("SELECT value FROM map WHERE key=?", (key,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise KeyError(key)

        def __delitem__(self, key):
            cursor = self._cur
            cursor.execute("DELETE FROM map WHERE key=?", (key,))

        def __contains__(self, key):
            cursor = self._cur
            cursor.execute("SELECT 1 FROM map WHERE key=?", (key,))
            return cursor.fetchall() != []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.__del__()
