# # Create a utitility function that adds playlist id to content.playlists in in many contents

from typing import List, Union
from bson import ObjectId
from src.datamodel.database.domain.DigitalSignage import Content, Playlist

async def update_content_playlist_references(content_ids: List[str], playlist_id: str) -> None:

    try:
        for content_id in content_ids:
            content = await Content.find_one({"content_id": content_id})
      
            if not content:
                try:
                    if ObjectId.is_valid(content_id):
                        content = await Content.get(ObjectId(content_id))
                except Exception:
                    continue 

            if content:
                if not content.playlists:
                    content.playlists = []
                if playlist_id not in content.playlists:
                    content.playlists.append(playlist_id)
                    await content.save()
            else:
                print(f"Content not found for ID: {content_id}")
                
    except Exception as e:
        print(f"Error updating content-playlist references: {str(e)}")