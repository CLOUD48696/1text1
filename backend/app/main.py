import asyncio
import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT, Settings
from app.database import StateConflict, Store
from app.schemas import CreateDiscussion
from app.seed import seed
from app.services.runner import Engine


def create_app(settings=None, client=None):
    settings = settings or Settings()
    store = Store(settings.database_url)
    engine = Engine(store, settings, client)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        store.interrupt_unfinished()
        if settings.seed_on_start: await seed(store)
        yield
        await engine.close()
        store.engine.dispose()

    app = FastAPI(title='AI Panel Studio', version='0.1.0', lifespan=lifespan)
    app.state.store, app.state.engine = store, engine

    @app.exception_handler(KeyError)
    async def missing(_, error): return JSONResponse(status_code=404, content={'code': 'not_found', 'message': '讨论不存在', 'retryable': False})

    @app.exception_handler(StateConflict)
    async def conflict(_, error): return JSONResponse(status_code=409, content={'code': 'invalid_state', 'message': str(error), 'retryable': False})

    @app.exception_handler(RequestValidationError)
    async def invalid(_, error): return JSONResponse(status_code=422, content={'code': 'invalid_input', 'message': '请提供 4–240 字的话题、2–6 位专家及有效参数', 'retryable': False})

    @app.get('/api/health')
    async def health(): return {'status': 'ok', 'mode': settings.app_mode}

    @app.get('/api/discussions')
    async def discussions(limit: int = Query(50, ge=1, le=100), cursor: int = Query(0, ge=0),
                          filter: Literal['all', 'active', 'completed'] = 'all'):
        return store.list(limit, cursor, filter)

    @app.post('/api/discussions', status_code=202)
    async def create(body: CreateDiscussion):
        room = engine.create(body.topic, body.expert_count)
        return {'discussion_id': room['id'], 'status': room['status']}

    @app.get('/api/discussions/{did}')
    async def snapshot(did: str): return store.snapshot(did)

    @app.post('/api/discussions/{did}/start', status_code=202)
    async def start(did: str): return engine.start(did)

    @app.post('/api/discussions/{did}/retry-generation', status_code=202)
    async def retry(did: str):
        engine.retry_generation(did)
        return {'discussion_id': did, 'status': 'generating'}

    @app.get('/api/discussions/{did}/events')
    async def events(did: str, request: Request, after: int = Query(0, ge=0), last_event_id: str | None = Header(None)):
        state = store.snapshot(did)
        try:
            cursor = int(last_event_id) if last_event_id is not None else after
            if cursor < 0 or cursor > state['last_event_sequence']: raise ValueError()
        except ValueError:
            return JSONResponse(status_code=422, content={'code': 'invalid_cursor', 'message': '事件游标无效，请刷新恢复', 'retryable': False})

        async def stream():
            nonlocal cursor
            heartbeats = 0
            while not await request.is_disconnected():
                batch = store.events(did, cursor)
                for event in batch:
                    cursor = event['sequence']
                    yield f'id: {cursor}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n'
                current = store.snapshot(did)
                if current['discussion']['status'] in ('completed', 'failed', 'interrupted') and cursor >= current['last_event_sequence']:
                    break
                heartbeats += 1
                if heartbeats % 40 == 0: yield ': heartbeat\n\n'
                await asyncio.sleep(0.25)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.get('/api/{path:path}')
    async def unknown(path: str):
        return JSONResponse(status_code=404, content={'code': 'not_found', 'message': '接口不存在', 'retryable': False})

    build = ROOT / 'frontend' / 'dist'
    if build.exists(): app.mount('/', StaticFiles(directory=build, html=True), name='frontend')
    return app


app = create_app()
