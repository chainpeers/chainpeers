from fastapi import FastAPI, HTTPException, status, Request, Body
from fastapi.responses import JSONResponse, HTMLResponse
from models import Peer, Base, Slice, SliceResults
from database import SessionLocal, engine
import json
from pydantic import BaseModel
from sqlalchemy.orm import class_mapper
from fastapi.templating import Jinja2Templates


app = FastAPI()
Base.metadata.create_all(bind=engine)
open_slices = []
templates = Jinja2Templates(directory='templates')


def serialize(model_instance):
    """Transforms a model instance into a dictionary."""
    columns = [c.key for c in class_mapper(model_instance.__class__).columns]
    return {c: getattr(model_instance, c) for c in columns}

@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    opened = db.query(Slice).filter(Slice.is_open == True).all()
    for op in opened:
        open_slices.append(op.id)


class SliceRequest(BaseModel):
    time: str
    starting_peers: str
    chain: str


class RegisterRequest(BaseModel):
    slice_id: str
    peer_list: str


@app.post("/start_slice")
async def start_slice(slice_request: SliceRequest = Body(...)):
    peer_pack = []
    db = SessionLocal()
    new_slice = Slice(time=slice_request.time, chain_name=slice_request.chain, starting_peers=slice_request.starting_peers, is_open=True)
    db.add(new_slice)
    db.commit()
    db.refresh(new_slice)
    new_slice_id = new_slice.id
    open_slices.append(new_slice_id)

    peer_list = json.loads(slice_request.starting_peers)
    for peer in peer_list:
        new_peer = Peer(address=peer['address'], version=peer['version'], time=slice_request.time,
                        score=peer['score'], is_starting=True)
        db.add(new_peer)
        db.commit()
        db.refresh(new_peer)
        new_peer_id = new_peer.id
        peer_pack.append(new_peer_id)

    new_slice_res = SliceResults(slice_id=new_slice_id, peer_ids=peer_pack)
    db.add(new_slice_res)
    db.commit()
    db.refresh(new_slice_res)
    db.close()
    response = {"id": new_slice_id}
    headers = {"Content-Type": "application/json"}
    return JSONResponse(content=response, headers=headers, status_code=201)


@app.post("/register_peers")
async def register_peers(register_request: RegisterRequest = Body(...)):
    peer_pack = []
    slice_id = int(register_request.slice_id)
    if slice_id in open_slices:
        db = SessionLocal()
        peer_list = json.loads(register_request.peer_list)
        for peer in peer_list:
            new_peer = Peer(address=peer['address'], version=peer['version'])
            db.add(new_peer)
            db.commit()
            db.refresh(new_peer)
            new_peer_id = new_peer.id
            peer_pack.append(new_peer_id)
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



