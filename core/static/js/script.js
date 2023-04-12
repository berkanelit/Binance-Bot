const socket = io(`http://${ip}:${port}`);

const class_data_mapping = {
  'trader-state': 'runtime_state',
  'trader-lastupdate': 'last_update_time',
  'trader-lastprice': 'lastPrice',
  'trader-markettype': 'order_market_type',
  'trader-orderside': 'order_side',
  'trader-ordertype': 'order_type',
  'trader-orderstatus': 'order_status',
  'trader-buyprice': 'price',
  'trader-sellprice': 'price',
  'trader-orderpoint': 'order_point'
};

let current_chart = '';
let update_chart = false;

$(document).ready(() => {
  socket.on('current_traders_data', (data) => {
    update_trader_results(data);
  });
});

function update_trader_results(data) {
  const currentTraders = data.data;
  let overall_total_trades = 0;
  let overall_total_pl = 0;

  for (let x = 0; x < currentTraders.length; x++) {
    const current = currentTraders[x];
    const trade_recorder = current.trade_recorder;
    const update_targets = [`trader_${current.market}`, `overview_${current.market}`];

    for (let i = 0; i < update_targets.length; i++) {
      const trader_panel = document.getElementById(update_targets[i]);
      let target_el = null;

      for (const key in class_data_mapping) {
        target_el = trader_panel.getElementsByClassName(key);
        if (target_el.length != 0) {
          const show_val = current.order_side === 'SELL' && key === 'trader-buyprice'
            ? trade_recorder[trade_recorder.length - 1][1]
            : current[class_data_mapping[key]];

          if (show_val === null) {
            target_el[0].innerText = 'Null';
          } else {
            target_el[0].innerText = show_val;
          }
        }
      }

      target_el = trader_panel.getElementsByClassName('show-sellaction');
      if (target_el.length !== 0) {
        target_el[0].style.display = current.order_side === 'SELL' ? 'block' : 'none';
      }

      let outcome = 0;
      let total_trades = 0;
      if (trade_recorder.length >= 2) {
        const range = trade_recorder.length / 2;
        for (let y = 0; y < range; y++) {
          const buy_order = trade_recorder[(range * 2) - 2];
          const sell_order = trade_recorder[range * 2 - 1];
          const buy_value = buy_order[1] * buy_order[2];
          const sell_value = sell_order[1] * buy_order[2];
          if (buy_order[3].includes('SHORT')) {
            outcome += buy_value - sell_value;
          } else {
            outcome += sell_value - buy_value;
          }
          total_trades += 1;
        }
      }

      const r_outcome = Math.round(outcome * 100000000) / 100000000;
      target_el = trader_panel.getElementsByClassName('trader-trades')[0];
      target_el.innerText = total_trades;
      target_el = trader_panel.getElementsByClassName('trader-overall')[0];
      target_el.innerText = r_outcome;

      if (update_targets[i] !== `overview_${current.market}`) {
        overall_total_trades += total_trades;
        overall_total_pl += r_outcome;
      }

      if (current_chart === update_targets[i] && update_chart === true && current_chart !== 'trader_Overview') {
        update_chart = false;
        target_el = trader_panel.getElementsByClassName('trader_charts')[0];
        build_chart(current.market, target_el);
      }
    }
  }

  const overview_section = document.getElementById('trader_Overview');
  let target_el = overview_section.getElementsByClassName('overview-totalpl')[0];
  target_el.innerText = overall_total_pl;
  target_el = overview_section.getElementsByClassName('overview-totaltrades')[0];
  target_el.innerText = overall_total_trades;
}

function hide_section(e, section_id) {
  const section_el = document.getElementsByTagName('section');
  for (let i = 0; i < section_el.length; i++) {
    if (section_el[i].id === `trader_${section_id}`) {
      current_chart = `trader_${section_id}`;
      update_chart = true;
      section_el[i].style.display = 'block';
    } else {
      section_el[i].style.display = 'none';
    }
  }
}

function start_trader(e, market_pair) {
  e.preventDefault();
  rest_api('POST', 'trader_update', { action: 'start', market: market_pair });
}

function pause_trader(e, market_pair) {
  e.preventDefault();
  rest_api('POST', 'trader_update', { action: 'pause', market: market_pair });
}

function build_chart(market_pair, element) {
  rest_api('GET', `get_trader_charting?market=${market_pair}&limit=200`, null, initial_build, element);
}

function rest_api(method, endpoint, data = null, target_function = null, target_element = null) {
  console.log(`'M: ${method}, ULR: /rest-api/v1/${endpoint}, D:${data}`);
  const request = new XMLHttpRequest();
  request.open(method, `/rest-api/v1/${endpoint}`, true);

  request.onload = function () {
    if (this.status === 200) {
      const resp_data = JSON.parse(request.responseText);
      console.log(resp_data);
      if (target_function !== null && target_element === null) {
        target_function(resp_data);
      } else if (target_function !== null && target_element !== null) {
        target_function(target_element, resp_data.data);
      }
    } else {
      console.log(`error ${request.status} ${request.statusText}`);
    }
  };

  if (data === null) {
    request.send();
  } else {
    request.setRequestHeader('content-type', 'application/json');
    request.send(JSON.stringify(data));
  }
}
