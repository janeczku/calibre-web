{% extends "layout.html" %}
{% block body %}
{% if g.user.show_detail_random() %}
<div class="discover random-books">
  <h2 class="random-books">{{_('Discover (Random Books)')}}</h2>
  <div class="row display-flex">
   {% for entry in random %}
    <div class="col-sm-3 col-lg-2 col-xs-6 book" id="books_rand">
      <div class="cover">
          <a href="{{ url_for('web.show_book', book_id=entry.id) }}" data-toggle="modal" data-target="#bookDetailsModal" data-remote="false">
              <span class="img">
                <img title="{{ entry.title }}" src="{{ url_for('web.get_cover', book_id=entry.id) }}" alt="{{ entry.title }}" />
                {% if entry.id in read_book_ids %}<span class="badge read glyphicon glyphicon-ok"></span>{% endif %}
              </span>
          </a>
      </div>
      <div class="meta">
        <a href="{{ url_for('web.show_book', book_id=entry.id) }}" data-toggle="modal" data-target="#bookDetailsModal" data-remote="false">
          <p title="{{entry.title}}" class="title">{{entry.title|shortentitle}}</p>
        </a>
        <p class="author">
          {% for author in entry.authors %}
            {% if loop.index > g.config_authors_max and g.config_authors_max != 0 %}
              {% if not loop.first %}
                <span class="author-hidden-divider">&amp;</span>
			  {% endif %}
              <a class="author-name author-hidden" href="{{url_for('web.books_list',  data='author', sort_param='new', book_id=author.id) }}">{{author.name.replace('|',',')|shortentitle(30)}}</a>
              {% if loop.last %}
                <a href="#" class="author-expand" data-authors-max="{{g.config_authors_max}}" data-collapse-caption="({{_('reduce')}})">(...)</a>
              {% endif %}
            {% else %}
              {% if not loop.first %}
                <span>&amp;</span>
              {% endif %}
              <a class="author-name" href="{{url_for('web.books_list',  data='author', sort_param='new', book_id=author.id) }}">{{author.name.replace('|',',')|shortentitle(30)}}</a>
            {% endif %}
          {% endfor %}
        </p>
        {% if entry.series.__len__() > 0 %}
        <p class="series">
          <a href="{{url_for('web.books_list', data='series', sort_param='new', book_id=entry.series[0].id )}}">
            {{entry.series[0].name}}
          </a>
          ({{entry.series_index|formatseriesindex}})
        </p>
        {% endif %}
        {% if entry.ratings.__len__() > 0 %}
        <div class="rating">
          {% for number in range((entry.ratings[0].rating/2)|int(2)) %}
            <span class="glyphicon glyphicon-star good"></span>
            {% if loop.last and loop.index < 5 %}
              {% for numer in range(5 - loop.index) %}
                <span class="glyphicon glyphicon-star-empty"></span>
              {% endfor %}
            {% endif %}
          {% endfor %}
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
{% endif %}
<div class="discover load-more">
  <h2 class="{{title}}">{{title}}</h2>
    <div class="filterheader hidden-xs hidden-sm">
      <a data-toggle="tooltip" title="{{_('Sort according to book date, newest first')}}" id="new" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='new')}}"><span class="glyphicon glyphicon-book"></span> <span class="glyphicon glyphicon-calendar"></span><span class="glyphicon glyphicon-sort-by-order"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort according to book date, oldest first')}}" id="old" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='old')}}"><span class="glyphicon glyphicon-book"></span> <span class="glyphicon glyphicon-calendar"></span><span class="glyphicon glyphicon-sort-by-order-alt"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort title in alphabetical order')}}" id="asc" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='abc')}}"><span class="glyphicon glyphicon-font"></span><span class="glyphicon glyphicon-sort-by-alphabet"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort title in reverse alphabetical order')}}" id="desc" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='zyx')}}"><span class="glyphicon glyphicon-font"></span><span class="glyphicon glyphicon-sort-by-alphabet-alt"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort authors in alphabetical order')}}" id="auth_az" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='authaz')}}"><span class="glyphicon glyphicon-user"></span><span class="glyphicon glyphicon-sort-by-alphabet"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort authors in reverse alphabetical order')}}" id="auth_za" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='authza')}}"><span class="glyphicon glyphicon-user"></span><span class="glyphicon glyphicon-sort-by-alphabet-alt"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort according to publishing date, newest first')}}" id="pub_new" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='pubnew')}}"><span class="glyphicon glyphicon-calendar"></span><span class="glyphicon glyphicon-sort-by-order"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort according to publishing date, oldest first')}}" id="pub_old" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='pubold')}}"><span class="glyphicon glyphicon-calendar"></span><span class="glyphicon glyphicon-sort-by-order-alt"></span></a>
      {% if page == 'series' %}
      <a data-toggle="tooltip" title="{{_('Sort ascending according to series index')}}" id="series_asc" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='seriesasc')}}"><span class="glyphicon glyphicon-sort-by-order"></span></a>
      <a data-toggle="tooltip" title="{{_('Sort descending according to series index')}}" id="series_desc" class="btn btn-primary" href="{{url_for('web.books_list', data=page, book_id=id, sort_param='seriesdesc')}}"><span class="glyphicon glyphicon-sort-by-order-alt"></span></a>
      {% endif %}
    </div>

  <div class="row display-flex">
    {% if entries[0] %}
    {% for entry in entries %}
    <div class="col-sm-3 col-lg-2 col-xs-6 book" id="books">
      <div class="cover">
          <a href="{{ url_for('web.show_book', book_id=entry.id) }}" data-toggle="modal" data-target="#bookDetailsModal" data-remote="false">
            <span class="img">
              <img title="{{ entry.title }}" src="{{ url_for('web.get_cover', book_id=entry.id) }}" alt="{{ entry.title }}"/>
              {% if entry.id in read_book_ids %}<span class="badge read glyphicon glyphicon-ok"></span>{% endif %}
            </span>
          </a>
      </div>
      <div class="meta">
        <a href="{{ url_for('web.show_book', book_id=entry.id) }}" data-toggle="modal" data-target="#bookDetailsModal" data-remote="false">
          <p title="{{ entry.title }}" class="title">{{entry.title|shortentitle}}</p>
        </a>
        <p class="author">
          {% for author in entry.authors %}
            {% if loop.index > g.config_authors_max and g.config_authors_max != 0 %}
              {% if not loop.first %}
                <span class="author-hidden-divider">&amp;</span>
			  {% endif %}
              <a class="author-name author-hidden" href="{{url_for('web.books_list', data='author', book_id=author.id, sort_param='new') }}">{{author.name.replace('|',',')|shortentitle(30)}}</a>
              {% if loop.last %}
                <a href="#" class="author-expand" data-authors-max="{{g.config_authors_max}}" data-collapse-caption="({{_('reduce')}})">(...)</a>
              {% endif %}
            {% else %}
              {% if not loop.first %}
                <span>&amp;</span>
              {% endif %}
              <a class="author-name" href="{{url_for('web.books_list', data='author', book_id=author.id, sort_param='new') }}">{{author.name.replace('|',',')|shortentitle(30)}}</a>
            {% endif %}
          {% endfor %}
          {% for format in entry.data %}
            {% if format.format|lower in g.constants.EXTENSIONS_AUDIO %}
            <span class="glyphicon glyphicon-music"></span>
            {% endif %}
          {%endfor%}
        </p>
        {% if entry.series.__len__() > 0 %}
        <p class="series">
          <a href="{{url_for('web.books_list', data='series', sort_param='new', book_id=entry.series[0].id )}}">
            {{entry.series[0].name}}
          </a>
          ({{entry.series_index|formatseriesindex}})
        </p>
        {% endif %}
        {% if entry.ratings.__len__() > 0 %}
        <div class="rating">
          {% for number in range((entry.ratings[0].rating/2)|int(2)) %}
            <span class="glyphicon glyphicon-star good"></span>
            {% if loop.last and loop.index < 5 %}
              {% for numer in range(5 - loop.index) %}
                <span class="glyphicon glyphicon-star-empty"></span>
              {% endfor %}
            {% endif %}
          {% endfor %}
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  {% endif %}
  </div>
</div>
{% endblock %}
