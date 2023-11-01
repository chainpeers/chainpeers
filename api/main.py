from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from models import Peer, Base, Slice, SliceResults
from api.database import SessionLocal, engine
from sqlalchemy.orm import class_mapper
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
import logging
import gzip
import json

app = FastAPI()
Base.metadata.create_all(bind=engine)
open_slices = []
templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)
gunicorn_error_logger = logging.getLogger("gunicorn.error")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers


def serialize(model_instance):
    """Transforms a model instance into a dictionary."""
    columns = [c.key for c in class_mapper(model_instance.__class__).columns]
    return {c: getattr(model_instance, c) for c in columns}


@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    opened = db.query(Slice).filter(Slice.is_open is True).all()
    for op in opened:
        open_slices.append(op.id)


@app.post("/start_slice")
async def start_slice(request: Request):
    compressed_data = await request.body()
    decompressed_data = gzip.decompress(compressed_data)
    slice_request = json.loads(decompressed_data.decode('utf-8'))
    db = SessionLocal()
    new_slice = Slice(time=slice_request['time'], chain_name=slice_request['chain'],
                      starting_peers=slice_request['starting_peers'], is_open=True)
    print('i created')
    db.add(new_slice)
    db.commit()
    db.refresh(new_slice)
    new_slice_id = new_slice.id
    open_slices.append(new_slice_id)
    peer_list = json.loads(slice_request['starting_peers'])
    peers = [dict(address=peer['address'],
                  version=peer['version'],
                  score=peer['score'],
                  time=slice_request['time'],
                  is_starting=True)
             for peer in peer_list]
    db.bulk_insert_mappings(Peer, peers)
    db.commit()
    peer_pack = [peer.id for peer in
                 db.query(Peer.id).filter(Peer.address.in_([peer['address'] for peer in peers]))]

    new_slice_res = SliceResults(slice_id=new_slice_id, peer_ids=peer_pack)
    db.add(new_slice_res)
    db.commit()
    db.refresh(new_slice_res)
    db.close()
    response = {"id": new_slice_id}
    headers = {"Content-Type": "application/json"}
    return JSONResponse(content=response, headers=headers, status_code=201)


@app.post("/register_peers")
async def register_peers(request: Request):
    compressed_data = await request.body()
    decompressed_data = gzip.decompress(compressed_data)
    register_request = json.loads(decompressed_data.decode('utf-8'))
    slice_id = int(register_request['slice_id'])
    if slice_id in open_slices:
        db = SessionLocal()
        peer_list = json.loads(register_request['peer_list'])
        peers = [dict(address=peer['address'], version=peer['version'], score=peer['score'], time=register_request['time']) for peer in peer_list]
        db.bulk_insert_mappings(Peer, peers)
        db.commit()
        peer_pack = [peer.id for peer in
                     db.query(Peer.id).filter(Peer.address.in_([peer['address'] for peer in peers]))]
        new_slice_res = db.query(SliceResults).filter(SliceResults.slice_id == slice_id).first()
        if new_slice_res:
            new_slice_res.peer_ids = new_slice_res.peer_ids + peer_pack
        else:
            new_slice_res = SliceResults(slice_id=slice_id, peer_ids=peer_pack)
            db.add(new_slice_res)
        db.commit()
        db.refresh(new_slice_res)
        db.close()
        response = {"id": slice_id}
        headers = {"Content-Type": "application/json"}
        return JSONResponse(content=response, headers=headers, status_code=201)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slice is not opened")


@app.post("/finish_slice")
async def finish_slice(slice_id):
    db = SessionLocal()
    slice_id = int(slice_id)
    open_slices.remove(slice_id)
    if db.query(Slice).filter(Slice.id == slice_id).first().is_open:
        db.query(Slice).filter(Slice.id == slice_id).first().is_open = False
        db.commit()
        response = {"id": slice_id}
        headers = {"Content-Type": "application/json"}
        db.close()
        return JSONResponse(content=response, headers=headers, status_code=200)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slice is not opened")


@app.post("/cancel_slice")
async def cancel_slice(slice_id):
    slice_id = int(slice_id)
    if slice_id in open_slices:
        db = SessionLocal()
        that_slice = db.query(Slice).filter_by(id=slice_id)
        if db.query(SliceResults).filter(SliceResults.slice_id == slice_id).first():
            slice_res = db.query(SliceResults).filter_by(slice_id=slice_id)
            slice_res_peers = db.query(SliceResults).filter(SliceResults.slice_id == slice_id).first().peer_ids
            if slice_res_peers:
                for peer_id in slice_res_peers:
                    db.query(Peer).filter_by(id=peer_id).delete()
            slice_res.delete()
        that_slice.delete()
        db.commit()
        db.close()
        open_slices.remove(slice_id)
        response = {"id": slice_id}
        headers = {"Content-Type": "application/json"}
        return JSONResponse(content=response, headers=headers, status_code=200)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slice is not opened")


@app.post("/delete_slice")
async def delete_slice(slice_id):
    slice_id = int(slice_id)
    if slice_id not in open_slices:
        db = SessionLocal()
        if db.query(Slice).filter(Slice.id == slice_id).first():
            that_slice = db.query(Slice).filter_by(id=slice_id)
            if db.query(SliceResults).filter(SliceResults.slice_id == slice_id).first():
                slice_res = db.query(SliceResults).filter_by(slice_id=slice_id)
                slice_res_peers = db.query(SliceResults).filter(SliceResults.slice_id == slice_id).first().peer_ids
                if slice_res_peers:
                    for peer_id in slice_res_peers:
                        db.query(Peer).filter_by(id=peer_id).delete()
                slice_res.delete()
            that_slice.delete()
            db.commit()
            db.close()
            response = {"id": slice_id}
            headers = {"Content-Type": "application/json"}
            return JSONResponse(content=response, headers=headers, status_code=200)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such slice")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Close before delete")


@app.get("/all_data_get/")
async def get_all_peer_data():
    db = SessionLocal()
    peer_data = db.query(Peer).all()
    slice_data = db.query(Slice).all()
    connection_data = db.query(SliceResults).all()
    db.close()
    data = {'peer_data': peer_data, 'slice_data': slice_data, 'slice_results_data': connection_data}
    return data


@app.get("/peers/{version}")
async def get_peers(version: str):
    version = str(version)
    db = SessionLocal()
    peers = db.query(Peer).filter(Peer.version == version).all()
    db.close()
    peers = [serialize(peer) for peer in peers]
    data = {'peers': peers}
    return data


@app.get("/", response_class=HTMLResponse)
def show_data(request: Request):
    db = SessionLocal()
    peer_data = db.query(Peer).all()
    slice_data = db.query(Slice).all()
    connection_data = db.query(SliceResults).all()
    db.close()
    data = {'peer_data': peer_data, 'slice_data': slice_data, 'slice_results_data': connection_data}
    return templates.TemplateResponse("index.html", {"request": request, "data": data})
