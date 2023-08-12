from fastapi import FastAPI
from models import Peer, Base, Slice, SliceResults
from database import SessionLocal, engine
import json
app = FastAPI()
Base.metadata.create_all(bind=engine)
open_slices = []


@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    opened = db.query(Slice).filter(Slice.is_open == True).all()
    for op in opened:
        open_slices.append(op.id)


@app.post("/start_slice")
def start_slice(time, starting_peers, chain):
    peer_pack = []
    db = SessionLocal()
    new_slice = Slice(time=time, chain_name=chain, starting_peers=starting_peers, is_open=True)
    db.add(new_slice)
    db.commit()
    db.refresh(new_slice)
    new_slice_id = new_slice.id
    open_slices.append(new_slice_id)

    peer_list = json.loads(starting_peers)
    for peer in peer_list:
        new_peer = Peer(address=peer['address'], version=peer['version'], is_starting=True)
        db.add(new_peer)
        db.commit()
        db.refresh(new_peer)
        new_peer_id = new_peer.id
        peer_pack.append(new_peer_id)

    new_slice_res = SliceResults(slice_id=new_slice_id, peer_ids=peer_pack)
    db.add(new_slice_res)
    db.commit()
    db.refresh(new_slice_res)
    data = {"new_slice_id": new_slice_id}
    return data


@app.post("/register_peers")
def register_peers(slice_id, peer_list):
    peer_pack = []
    slice_id = int(slice_id)
    if slice_id in open_slices:
        db = SessionLocal()
        peer_list = json.loads(peer_list)
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
        return f'slice {slice_id} was updated'
    else:
        return "slice is not open"


@app.post("/finish_slice")
def finish_slice(slice_id):
    db = SessionLocal()
    slice_id = int(slice_id)
    open_slices.remove(slice_id)
    db.query(Slice).filter(Slice.id == slice_id).first().is_open = False
    db.commit()
    return f'slice {slice_id} is finished'


@app.post("/cancel_slice")
def cancel_slice(slice_id):
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
        open_slices.remove(slice_id)
        return f'slice {slice_id} was canceled'
    else:
        return f'slice {slice_id} was not opened'


@app.post("/delete_slice")
def delete_slice(slice_id):
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
            return f'slice {slice_id} was deleted'
        else:
            return "No such slice"
    else:
        return f'Slice {slice_id} is open. Cancel before delete'


@app.get("/all_data_get/")
def get_all_peer_data():
    db = SessionLocal()
    peer_data = db.query(Peer).all()
    slice_data = db.query(Slice).all()
    connection_data = db.query(SliceResults).all()
    data = {'peer data': peer_data, 'slice data': slice_data, 'slice_results_data': connection_data}
    return data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

