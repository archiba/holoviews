from __future__ import absolute_import, division, unicode_literals

import base64
import json
import re

import panel as pn

import param
with param.logging_level('CRITICAL'):
    from plotly import utils
    import plotly.graph_objs as go

from ..renderer import Renderer, MIME_TYPES, HTML_TAGS
from ...core.options import Store
from ...core import HoloMap


class PlotlyRenderer(Renderer):

    backend = param.String(default='plotly', doc="The backend name.")

    fig = param.ObjectSelector(default='auto', objects=['html', 'json', 'png', 'svg', 'auto'], doc="""
        Output render format for static figures. If None, no figure
        rendering will occur. """)

    mode_formats = {'fig': {'default': ['html', 'png', 'svg', 'json']},
                    'holomap': {'default': ['widgets', 'scrubber', 'auto']}}

    widgets = ['scrubber', 'widgets']

    _loaded = False

    def __call__(self, obj, fmt='html', divuuid=None):
        plot, fmt =  self._validate(obj, fmt)
        mime_types = {'file-ext':fmt, 'mime_type': MIME_TYPES[fmt]}

        if fmt in ('html', 'png', 'svg'):
            return self._figure_data(plot, fmt, divuuid=divuuid), mime_types
        elif fmt == 'json':
            return self.diff(plot), mime_types


    def diff(self, plot, serialize=True):
        """
        Returns a json diff required to update an existing plot with
        the latest plot data.
        """
        diff = plot.state
        if serialize:
            return json.dumps(diff, cls=utils.PlotlyJSONEncoder)
        else:
            return diff


    def _figure_data(self, plot, fmt=None, divuuid=None, comm=True, as_script=False, width=800, height=600):
        # Wrapping plot.state in go.Figure here performs validation
        # and applies any default theme.
        figure = go.Figure(plot.state)

        if fmt in ('png', 'svg'):
            import plotly.io as pio
            data = pio.to_image(figure, fmt)
            if as_script:
                b64 = base64.b64encode(data).decode("utf-8")
                (mime_type, tag) = MIME_TYPES[fmt], HTML_TAGS[fmt]
                src = HTML_TAGS['base64'].format(mime_type=mime_type, b64=b64)
                div = tag.format(src=src, mime_type=mime_type, css='')
                js = ''
                return div, js
            return data

        figure_pane = pn.pane.Plotly(figure)
        mimebundle = figure_pane._repr_mimebundle_()
        html = mimebundle[0]['text/html']

        if as_script:
            script_ind = html.find('<script')
            just_html, script_with_tags = html[:script_ind], html[script_ind:]
            just_script = re.sub(r"(<script[^>]*>)|(</script>)", "", script_with_tags)
            return just_html, just_script

        return html

    @classmethod
    def plot_options(cls, obj, percent_size):
        factor = percent_size / 100.0
        obj = obj.last if isinstance(obj, HoloMap) else obj
        plot = Store.registry[cls.backend].get(type(obj), None)
        options = plot.lookup_options(obj, 'plot').options
        width = options.get('width', plot.width) * factor
        height = options.get('height', plot.height) * factor
        return dict(options, **{'width':int(width), 'height': int(height)})


    @classmethod
    def load_nb(cls, inline=True):
        """
        Loads the plotly notebook resources.
        """
        pn.extension("plotly")
