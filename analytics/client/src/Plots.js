import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Layer } from 'baseui/layer';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import { Select, TYPE } from 'baseui/select';
import { Checkbox, LABEL_PLACEMENT } from 'baseui/checkbox';
import Plot from 'react-plotly.js';
import * as aq from 'arquero';
import lodash from 'lodash';

import {AreaPopup, AreaToAreaPopup } from './Popup';
import {orderedTransportModeIdentifiers} from './transportModes';

const TOP_MARGIN = 20;
const BOTTOM_MARGIN = 110;

const getHeight = table => (table.numRows() * 20 + TOP_MARGIN + BOTTOM_MARGIN + 50);

export function TransportModesPlot({ transportModes, areaType, areaData, selectedTransportMode, rangeLength, weekSubset }) {
  if (!areaData)
    return <Spinner />;

  const modeOrder = orderedTransportModeIdentifiers(transportModes, selectedTransportMode);
  const primaryModes = transportModes.filter(m => !m.synthetic);
  const modeById = new Map(primaryModes.map(m => [m.identifier, m]));
  const availableModes = modeOrder.filter(mode => areaData.columnNames().includes(mode) && modeById.has(mode));
  const table = areaData
    .orderby(selectedTransportMode.identifier + '_rel');
  const areasById = new Map(areaType.areas.map(area => [parseInt(area.id), {...area}]))

  const traces = availableModes.map((mode) => {
    const x = [], y = [], customdata = [];
    table.objects().forEach(row => {
      const { areaId } = row;
      const area = areasById.get(areaId);
      if (!area) {
        console.warn('area not found');
        return;
      }
      const name = area.name + (areaType.identifier === 'tre:paavo' ? ` (${area.identifier})` : '');
      y.push(name);
      x.push(row[mode + '_rel']);

      const syntheticModes = transportModes.filter(m => m.synthetic).map(m =>
        Object.assign({}, m, {rel: row[m.identifier + '_rel'] * 100}));;
      customdata.push({
        abs: row[mode], syntheticModes, total: row['total']});
    });
    const trace = {
      name: modeById.get(mode).name,
      orientation: 'h',
      type: 'bar',
      x,
      y,
      customdata,
      marker: {
        color: modeById.get(mode).colors.primary,
        line: {
          color: '#ffffff',
          width: 1,
        }
      },
    };
    return trace;
  })
  const layout = {
    margin: {
      l: 160 + (areaType.identifier === 'tre:paavo' ? 40 : 0),
      r: 20,
      t: TOP_MARGIN,
      b: BOTTOM_MARGIN,
      pad: 5
    },
    height: getHeight(table),
    bargap: 0,
    barnorm: 'percent',
    xaxis: {
      showgrid: false,
      fixedrange: true,
      zeroline: false,
    },
    barmode: 'stack',
    dragmode: 'pan',
    legend: {
      traceorder: 'normal'
    },
  };
  const config = {
    responsive: true,
    editable: false,
    displayModeBar: false,
    dragmode: 'pan',
    //autosizable: true,
  };
  return (<TransportModePlotWrapper
            traces={traces}
            layout={layout}
            weekSubset={weekSubset}
            config={config}
            Popup={AreaPopup}
          />);

}

function AreaSelector ({ areas, selectedArea, setSelectedArea }) {
  const { t } = useTranslation();
  return <div style={{marginLeft: '20%', marginRight: '20%'}}>
    <Select
      closeOnSelect={true}
      ignoreCase={true}
      searchable={true}
      labelKey='label'
      valueKey='id'
      type={TYPE.search}
      value={selectedArea.id != null ? [selectedArea]: null}
      valueToLabel={() => 'foo'}
      placeholder={t('choose-area')}
      onChange={params => setSelectedArea(params.value[0].id)}
      options={areas}
    /></div>;
};

function ReflexiveTripsFilter({reflexiveTripsState}) {
  const [showReflexive, setReflexive] = reflexiveTripsState;
  const { t } = useTranslation();
  return <div style={{marginLeft: '20%', marginRight: '20%', marginTop: 10}}><Checkbox
           checked={showReflexive}
           onChange={e => setReflexive(e.target.checked)}
           labelPlacement={LABEL_PLACEMENT.right}>
           {t('show-reflexive-trips')}
         </Checkbox></div>
}

export function AreaBarChart({ transportModes, areaType, areaData, rangeLength, weekSubset, selectedArea, setSelectedArea }) {
  if (!areaData)
    return <Spinner />;
  selectedArea = { id: selectedArea };
  const areaSelector = <AreaSelector areas={areaType.areas.map(a => (
                                       {label: a.name + (
                                         areaType.identifier === 'tre:paavo' ? ` (${a.identifier})` : ''),
                                        id: Number.parseInt(a.id)}))}
                                     selectedArea={selectedArea}
                                     setSelectedArea={setSelectedArea}/>;

  if (selectedArea.id == null) {
    return areaSelector;
  }

  const modeOrder = orderedTransportModeIdentifiers(transportModes, 'walk');
  const primaryModes = transportModes.filter(m => !m.synthetic);
  const modeById = new Map(primaryModes.map(m => [m.identifier, m]));
  const availableModes = modeOrder.filter(mode => modeById.has(mode));

  const areasById = new Map(areaType.areas.map(area => [parseInt(area.id), {...area}]));

  const reflexiveTripsState = useState(true);

  const traces = availableModes.map((mode) => {
    const x = [], y = [], customdata = [];
    areaData.orderby('total').objects().forEach(row => {
      const { areaId } = row;
      if (reflexiveTripsState[0] === false && areaId === selectedArea.id) {
        return;
      }
      const area = areasById.get(areaId);
      if (!area) {
        console.warn('area not found');
        return;
      }
      const name = area.name + (areaType.identifier === 'tre:paavo' ? ` (${area.identifier})` : '');
      y.push(name);
      x.push(row[mode]);

      customdata.push({
        selectedArea: areasById.get(selectedArea.id),
        rel: row[`${mode}_rel`] * 100
      });
    });
    const trace = {
      name: modeById.get(mode).name,
      orientation: 'h',
      type: 'bar',
      x,
      y,
      customdata,
      marker: {
        color: modeById.get(mode).colors.primary,
        line: {
          color: '#ffffff',
          width: 1,
        }
      },
    };
    return trace;
  })
  const layout = {
    margin: {
      l: 160 + (areaType.identifier === 'tre:paavo' ? 40 : 0),
      r: 20,
      t: TOP_MARGIN,
      b: BOTTOM_MARGIN,
      pad: 5
    },
    height: getHeight(areaData),
    bargap: 0,
    xaxis: {
      showgrid: false,
      zeroline: false,
      fixedrange: true,
    },
    barmode: 'stack',
    dragmode: 'pan',
    legend: {
      traceorder: 'normal'
    },
  };
  const config = {
    responsive: true,
    editable: false,
    displayModeBar: false,
    dragmode: 'pan',
    //autosizable: true,
  };
  return (<>
            { areaSelector }
            <ReflexiveTripsFilter reflexiveTripsState={reflexiveTripsState} />
            <TransportModePlotWrapper
            traces={traces}
            layout={layout}
            weekSubset={weekSubset}
            config={config}
            Popup={AreaToAreaPopup}
          />
          </>);

}

const MemoizedPopupEnabledPlot = React.memo(Plot);

function TransportModePlotWrapper({traces, layout, config, weekSubset, Popup}) {
  const [popupState, setPopupState] = useState(null);
  const [hoverState, setHoverState] = useState({
    hover: false, event: null, point: null
  });
  const onHoverCallback = ({event, points: [point]}) => setHoverState({
    hover: true, event, point
  });
  const onUnhoverCallback = () => setHoverState({
    hover: false, event: null, point: null
  })
  const hoverHandler = ({event, point}) => {
    setPopupState(
      {area: {
        name: point.label,
      },
       transportMode: point.data.name,
       rel: point.customdata.rel ?? point.value,
       abs: point.customdata.abs ?? point.value,
       total: point.customdata.total,
       weekSubset,
       syntheticModes: point.customdata.syntheticModes,
       selectedArea: point.customdata.selectedArea,
       x: event.x,
       y: event.y});
  };
  useEffect(() => {
    let onHover, onUnhover;
    if (hoverState.hover === true) {
      const {event, point} = hoverState;
      onHover = lodash.throttle(() => hoverHandler({event, point}), 100);
      onUnhover?.cancel();
      onHover();
    }
    else {
      onUnhover = lodash.debounce(() => setPopupState(null), 200);
      onUnhover();
    }
    return () => {
      onHover?.cancel();
      onUnhover?.cancel();
    }
  }, [hoverState]);

  let popup = null;
  if (popupState !== null) {
    popup = <Popup {...popupState} />;
  }
  return <div style={{width: '100%'}}>
           <Layer>
             { popup || '' }
           </Layer>
           <MemoizedPopupEnabledPlot
             data={traces}
             layout={layout}
             config={config}
             style={{width: '100%'}}
             useResizeHandler
             onHover={onHoverCallback}
             onUnhover={onUnhoverCallback}
           />
         </div>
}
