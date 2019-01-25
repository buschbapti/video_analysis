import pandas as pd
import numpy as np
from itertools import combinations

from bokeh.plotting import figure, gridplot
from bokeh.colors import RGB
from bokeh.models import CategoricalColorMapper, HoverTool, ColumnDataSource, Panel
from bokeh.models.widgets import CheckboxGroup, Slider, RangeSlider, Tabs
from bokeh.layouts import column, row, WidgetBox
from bokeh.models.widgets import RadioButtonGroup
from bokeh.models import Range1d


class DatasetHandler(object):
    """docstring for DatasetHandle"""
    def __init__(self, filelist, colors_list, question_list=None):
        self.dataset = pd.DataFrame()
        for f in filelist:
            data = pd.read_csv(f)
            self.dataset = pd.concat([self.dataset, data], ignore_index=True)
        self.question_ids = list(self.dataset)[4:]
        if not question_list is None:
            self.question_ids = list(set(self.question_ids) & set(question_list))
            self.question_ids.sort()
        self.group_ids = ['Test subject', 'Technicians', 'Lab members', 'Team members']
        self.data_color = colors_list 
        
    def extract_data(self, group_list, data_type, id_list=None):
        subset = self.dataset.copy()
        if group_list is not None:
            subset = subset[subset['group'].isin(group_list)]
        if id_list is not None:
            assert all(idx in list(subset['ID']) for idx in id_list), "The selected subjects ID are not in this subset of the dataset"
            subset = subset[subset['ID'].isin(id_list)]
        subset = subset[subset['type'] == data_type]
        return subset

    def make_dataset_add(self, group_list, data_type, id_list=None):
        sources = {}
        subset = self.extract_data(group_list, data_type, id_list)
        if data_type == 2:
            bins = np.arange(12) - 5
        else:
            bins = np.arange(6) + 1
        # Iterate through all the questions
        for i, qid in enumerate(self.question_ids):
            dict_value = {}
            hist, edges = np.histogram(subset[qid], bins = bins)
            dict_value['score'] = hist
            dict_value['left'] = edges[:-1]-0.5
            dict_value['right'] = edges[1:]-0.5
            dict_value['ticks'] = bins[:-1]
            dict_value['color'] = self.data_color[data_type]
            frame = pd.DataFrame(dict_value)
            sources[qid] = ColumnDataSource(frame)
        return sources

    def make_dataset_comp(self, group_list, data_type, id_list=None):
        sources = {}
        for g in group_list:
            sources[self.group_ids[g]] = {}
            subset = self.extract_data([g], data_type, id_list)
            if data_type == 2:
                bins = np.arange(11) - 5
            else:
                bins = np.arange(6) + 1
            # Iterate through all the questions
            for i, qid in enumerate(self.question_ids):
                dict_value = {}
                hist, edges = np.histogram(subset[qid], bins = bins)
                dict_value['score'] = hist
                dict_value['left'] = edges[:-1]-0.5
                dict_value['right'] = edges[1:]-0.5
                dict_value['ticks'] = bins[:-1]
                dict_value['color'] = self.data_color[data_type]
                frame = pd.DataFrame(dict_value)
                sources[self.group_ids[g]][qid] = ColumnDataSource(frame)
        return sources

    @staticmethod
    def style(p):
        # Title 
        p.title.align = 'center'
        p.y_range = Range1d(0, 12)
        return p

    def make_plot(self, sources, add):
        plots = []
        for i, qid in enumerate(self.question_ids):
            # Blank plot with correct labels
            plots.append(figure(plot_width = 225, plot_height = 225, title = qid,
                         x_axis_label = 'Score', y_axis_label = 'Nb subjects'))
            if add:
                # Quad glyphs to create a histogram
                plots[-1].quad(source=sources[qid], bottom=0, top='score', left='left', right='right',
                               color='color', fill_alpha=.8, hover_fill_color='color',
                               hover_fill_alpha=1.0, line_color='black')
                # Hover tool with vline mode
                hover = HoverTool(tooltips=[('Score', '@ticks'),
                                            ('Number of answers', '@score')],
                                  mode='vline')
                plots[-1].add_tools(hover)
            else:
                for key, value in sources.items():
                    plots[-1].quad(source=value[qid], bottom=0, top='score', left='left', right='right',
                               color='color', fill_alpha=.8, hover_fill_color='color',
                               hover_fill_alpha=1.0, line_color='black')
                    # Hover tool with vline mode
                    hover = HoverTool(tooltips=[('Score', '@ticks'),
                                                ('Number of answers', '@score'),
                                                ('Group', key)],
                                      mode='vline')
                    plots[-1].add_tools(hover)
            plots[-1] = self.style(plots[-1])
        p = gridplot(plots, ncols=3)        
        return p

    def update_add(self, attr, old, new):
        groups_to_plot = [i+1 for i in self.group_selection_add.active]
        type_to_plot = self.type_selection_add.active 
        # Make a new dataset based on the selection
        new_src = self.make_dataset_add(groups_to_plot, type_to_plot)
        # Update the source used in the quad glpyhs
        for qid in self.question_ids:
            self.sources_add[qid].data.update(new_src[qid].data)

    def update_comp(self, attr, old, new):
        groups_to_plot = self.possible_groups[self.group_selection_comp.active]
        type_to_plot = self.type_selection_comp.active 
        # Make a new dataset based on the selection
        new_src = self.make_dataset_comp(groups_to_plot, type_to_plot)
        # Update the source used in the quad glpyhs
        for g in groups_to_plot:
            for qid in self.question_ids:
                self.sources_comp[self.group_ids[g]][qid].data.update(new_src[self.group_ids[g]][qid].data)

    def modify_doc(self, doc):
        # checkboxes for groups
        self.group_selection_add = CheckboxGroup(labels=self.group_ids, active = [0, 1])
        self.group_selection_add.on_change('active', self.update_add)
        initial_groups = [i+1 for i in self.group_selection_add.active]
        # radio button for data type
        self.type_selection_add = RadioButtonGroup(labels=["Prior", "After", "Diff"], active=0)
        self.type_selection_add.on_change('active', self.update_add)
        initial_type = self.type_selection_add.active
        # add control and initialize display
        controls = WidgetBox(self.group_selection_add, self.type_selection_add)
        self.sources_add = self.make_dataset_add(initial_groups, initial_type)
        # add two panels, one for adding
        p = self.make_plot(self.sources_add, True)
        layout = row(controls, p)
        tab1 = Panel(child=layout, title = 'Add')

        # # checkboxes for groups
        # self.possible_groups = list(combinations([1,2,3], 2))
        # labels = []
        # for pg in self.possible_groups:
        #     labels.append(self.group_ids[pg[0]] + ' vs ' + self.group_ids[pg[1]])
        # self.group_selection_comp = RadioButtonGroup(labels=labels, active=0)
        # self.group_selection_comp.on_change('active', self.update_comp)
        # initial_groups = self.possible_groups[self.group_selection_comp.active]
        # # radio button for data type
        # self.type_selection_comp = RadioButtonGroup(labels=["Prior", "After", "Diff"], active=0)
        # self.type_selection_comp.on_change('active', self.update_comp)
        # initial_type = self.type_selection_comp.active
        # # add control and initialize display
        # controls = WidgetBox(self.group_selection_comp, self.type_selection_comp)
        # self.sources_comp = {}
        # for i, g in enumerate(self.group_ids):
        #     # for initialization only
        #     self.sources_comp[g] = self.make_dataset_add([i], initial_type)
        # # add two panels, one for adding
        # p = self.make_plot(self.sources_comp, False)
        # layout = row(controls, p)
        # tab2 = Panel(child=layout, title = 'Compare')

        # Make a tab with the layouts 
        tabs = Tabs(tabs=[tab1])
        doc.add_root(tabs)
