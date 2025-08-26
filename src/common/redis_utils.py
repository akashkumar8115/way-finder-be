import orjson
import logging
import os
import gzip
import zlib
import asyncio
import time
from typing import Optional, Dict, Any, Union
import redis.asyncio as redis
from redis.exceptions import RedisError
import struct

logger = logging.getLogger(__name__)

# Optimized Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://default:qPnMFGTQMkSPtXaRdgvpNWSxImrwPopX@centerbeam.proxy.rlwy.net:41705")

# Ultra-optimized Redis client with minimal overhead
redis_client = redis.from_url(
    REDIS_URL,
    max_connections=50,           # Increased pool size
    socket_timeout=2.0,           # Reduced timeout
    socket_connect_timeout=2.0,   # Reduced connect timeout
    socket_keepalive=True,        # Keep connections alive
    socket_keepalive_options={},
    decode_responses=False,       # Work with bytes directly
    retry_on_timeout=True,
    retry_on_error=[],
    health_check_interval=60,
)

# Compression thresholds
LIGHT_COMPRESSION_THRESHOLD = 512   # 512 bytes
HEAVY_COMPRESSION_THRESHOLD = 2048  # 2KB

# Serialization formats
FORMATS = {
    'json': 1,
    'json_gz': 2,
    'json_zlib': 3,
}

def _ultra_fast_serialize(data: Any, compress: bool = True) -> bytes:
    """Ultra-fast serialization with optimal compression"""
    try:
        # Use orjson for maximum speed
        json_bytes = orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY)
        
        if not compress or len(json_bytes) < LIGHT_COMPRESSION_THRESHOLD:
            # Store format indicator + data
            return struct.pack('B', FORMATS['json']) + json_bytes
        
        # Choose compression method based on size
        if len(json_bytes) < HEAVY_COMPRESSION_THRESHOLD:
            # Use zlib for smaller payloads (faster)
            compressed = zlib.compress(json_bytes, level=1)  # Fast compression
            return struct.pack('B', FORMATS['json_zlib']) + compressed
        else:
            # Use gzip for larger payloads (better compression)
            compressed = gzip.compress(json_bytes, compresslevel=1)
            return struct.pack('B', FORMATS['json_gz']) + compressed
            
    except Exception as e:
        logger.error(f"Serialization error: {e}")
        raise

def _ultra_fast_deserialize(data: bytes) -> Any:
    """Ultra-fast deserialization with automatic decompression"""
    try:
        if len(data) < 1:
            return None
            
        # Read format indicator
        format_id = struct.unpack('B', data[:1])[0]
        payload = data[1:]
        
        if format_id == FORMATS['json']:
            # Raw JSON
            return orjson.loads(payload)
        elif format_id == FORMATS['json_zlib']:
            # zlib compressed
            decompressed = zlib.decompress(payload)
            return orjson.loads(decompressed)
        elif format_id == FORMATS['json_gz']:
            # gzip compressed
            decompressed = gzip.decompress(payload)
            return orjson.loads(decompressed)
        else:
            # Fallback - try direct orjson parsing
            return orjson.loads(payload)
            
    except Exception as e:
        logger.error(f"Deserialization error: {e}")
        raise

async def get_cache_fast(key: str, default: Any = None) -> Any:
    """Ultra-fast cache retrieval with minimal overhead"""
    try:
        # Single Redis call with timeout
        value = await asyncio.wait_for(redis_client.get(key), timeout=1.0)
        
        if value is None:
            return default
            
        return _ultra_fast_deserialize(value)
        
    except asyncio.TimeoutError:
        logger.warning(f"Redis timeout for key: {key}")
        return default
    except Exception as e:
        logger.warning(f"Redis GET error for {key}: {e}")
        return default

async def set_cache_fast(key: str, value: Any, expire: int = 600) -> bool:
    """Ultra-fast cache storage"""
    try:
        data = _ultra_fast_serialize(value)
        await asyncio.wait_for(redis_client.set(key, data, ex=expire), timeout=1.0)
        return True
    except Exception as e:
        logger.warning(f"Redis SET error for {key}: {e}")
        return False

async def get_compressed_cache(key: str, default: Any = None) -> Any:
    """Get cache with heavy compression for large payloads"""
    try:
        value = await redis_client.get(key)
        if value is None:
            return default
        return _ultra_fast_deserialize(value)
    except Exception as e:
        logger.warning(f"Compressed cache GET error: {e}")
        return default

async def set_compressed_cache(key: str, value: Any, expire: int = 600) -> bool:
    """Set cache with heavy compression"""
    try:
        data = _ultra_fast_serialize(value, compress=True)
        await redis_client.set(key, data, ex=expire)
        return True
    except Exception as e:
        logger.warning(f"Compressed cache SET error: {e}")
        return False

# Batch operations for multiple keys
async def get_multi_cache_fast(keys: list) -> Dict[str, Any]:
    """Get multiple cache values in one Redis call"""
    if not keys:
        return {}
        
    try:
        # Single mget call
        values = await redis_client.mget(keys)
        
        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                try:
                    result[key] = _ultra_fast_deserialize(value)
                except Exception as e:
                    logger.warning(f"Failed to deserialize {key}: {e}")
                    
        return result
    except Exception as e:
        logger.error(f"Multi-get error: {e}")
        return {}

async def set_multi_cache_fast(data: Dict[str, Any], expire: int = 600) -> bool:
    """Set multiple cache values using pipeline"""
    if not data:
        return True
        
    try:
        pipe = redis_client.pipeline()
        
        for key, value in data.items():
            try:
                serialized = _ultra_fast_serialize(value)
                pipe.set(key, serialized, ex=expire)
            except Exception as e:
                logger.warning(f"Failed to serialize {key}: {e}")
                
        await pipe.execute()
        return True
    except Exception as e:
        logger.error(f"Multi-set error: {e}")
        return False

# Background cache operations (non-blocking)
async def set_cache_background(key: str, value: Any, expire: int = 600):
    """Set cache in background without blocking"""
    try:
        data = _ultra_fast_serialize(value)
        # Fire and forget
        asyncio.create_task(redis_client.set(key, data, ex=expire))
    except Exception as e:
        logger.warning(f"Background cache set failed for {key}: {e}")

# Cache statistics
async def get_redis_stats() -> Dict[str, Any]:
    """Get Redis performance statistics"""
    try:
        info = await redis_client.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100
        }
    except Exception as e:
        logger.error(f"Redis stats error: {e}")
        return {}

# Connection health check
async def redis_health_check() -> bool:
    """Quick Redis health check"""
    try:
        start = time.perf_counter()
        await redis_client.ping()
        latency = (time.perf_counter() - start) * 1000
        
        if latency > 50:  # > 50ms is concerning
            logger.warning(f"High Redis latency: {latency:.1f}ms")
            
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False

# Cleanup function
async def close_redis_connection():
    """Clean shutdown of Redis connections"""
    try:
        await redis_client.close()
        logger.info("Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")