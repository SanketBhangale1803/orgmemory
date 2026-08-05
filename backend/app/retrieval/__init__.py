__all__ = ["RetrievalService"]


def __getattr__(name: str):
    # Keep semantic providers importable by the graph ranker without eagerly
    # importing RetrievalService back into the graph package.
    if name == "RetrievalService":
        from .service import RetrievalService

        return RetrievalService
    raise AttributeError(name)
