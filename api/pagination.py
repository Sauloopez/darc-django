from django.core.paginator import Paginator

class Pagination:
    def __init__(self, elements : list, pages = None, items_per_page = None) -> None:
        self._cached_pages = None
        self._elements = elements
        self._pages = pages
        self._items_per_page = items_per_page
        return

    def with_num_pages(self, pages):
        self._pages = pages
        return self

    def with_items_per_page(self, items_per_page):
        self._items_per_page = items_per_page
        return self

    @property
    def pages(self):
        elements = None
        paginator = None
        if self._cached_pages:
            return self._cached_pages
        if not self._elements:
            return []
        if self._pages and not self._items_per_page:
            items_per_page = (len(self._elements) / self._pages).__floor__() +1
            paginator = Paginator(self._elements, items_per_page)
            elements = {
                page: paginator.get_page(page).object_list
                for page in range(1, paginator.num_pages + 1)
            }
        if self._items_per_page and not self._pages:
            paginator = Paginator(self._elements, self._items_per_page)
            elements = {
                page: paginator.get_page(page).object_list
                for page in range(1, paginator.num_pages + 1)
            }
        if self._items_per_page and self._pages:
            paginator = Paginator(self._elements, self._items_per_page)
            elements = {
                page: paginator.get_page(page).object_list
                for page in range(1, self._pages+1)
            }

        del paginator
        self._cached_pages = elements
        return elements
    pass
